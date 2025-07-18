import pandas as pd
import numpy as np
from olist.utils import haversine_distance
from olist.data import Olist


class Order:
    '''
    DataFrames containing all orders as index,
    and various properties of these orders as columns
    '''
    def __init__(self):
        # Assign an attribute ".data" to all new instances of Order
        self.data = Olist().get_data()

    def get_wait_time(self, is_delivered=True):
        """
        Returns a DataFrame with:
        [order_id, wait_time, expected_wait_time, delay_vs_expected, order_status]
        and filters out non-delivered orders unless specified
        """
        orders = self.data['orders'].copy()

        if is_delivered:
            orders = orders[orders['order_status'] == 'delivered'].copy()

        # Convert string timestamps to pandas datetime objects
        date_columns = [
            'order_purchase_timestamp',
            'order_approved_at',
            'order_delivered_carrier_date',
            'order_delivered_customer_date',
            'order_estimated_delivery_date'
        ]
        for col in date_columns:
            if col in orders.columns:
                orders[col] = pd.to_datetime(orders[col])

        # Calculate wait times
        orders['wait_time'] = (
            orders['order_delivered_customer_date'] -
            orders['order_purchase_timestamp']
        ).dt.total_seconds() / (24 * 3600)

        orders['expected_wait_time'] = (
            orders['order_estimated_delivery_date'] -
            orders['order_purchase_timestamp']
        ).dt.total_seconds() / (24 * 3600)

        delay = (
            orders['order_delivered_customer_date'] -
            orders['order_estimated_delivery_date']
        ).dt.total_seconds() / (24 * 3600)

        orders['delay_vs_expected'] = np.maximum(delay, 0)

        return orders[['order_id', 'wait_time', 'expected_wait_time', 'delay_vs_expected', 'order_status']]

    def get_review_score(self):
        """
        Returns a DataFrame with:
        order_id, dim_is_five_star, dim_is_one_star, review_score
        """
        reviews = self.data['order_reviews'].copy()
        review_scores = reviews[['order_id', 'review_score']].copy()
    
        # Create binary flags for 5-star and 1-star reviews
        review_scores['dim_is_five_star'] = (review_scores['review_score'] == 5).astype(int)
        review_scores['dim_is_one_star'] = (review_scores['review_score'] == 1).astype(int)
        
        # Reorder columns to match the expected output
        result = review_scores[['order_id', 'dim_is_five_star', 'dim_is_one_star', 'review_score']]

        return result

    def get_number_items(self):
        """
        Returns a DataFrame with:
        order_id, number_of_items
        """
        items = self.data['order_items'].copy()
        result = items.groupby('order_id').size().reset_index(name='number_of_items')

        return result

    def get_number_sellers(self):
        """
        Returns a DataFrame with:
        order_id, number_of_sellers
        """
        items = self.data['order_items'].copy()
        sellers = self.data['sellers'].copy()
        merged = items.merge(sellers, on='seller_id', how='left')
        number_of_sellers = (
            merged.groupby('order_id')['seller_id']
            .nunique()
            .reset_index(name='number_of_sellers')
        )
        result = number_of_sellers[['order_id', 'number_of_sellers']]
        return result

    def get_price_and_freight(self):
        """
        Returns a DataFrame with:
        order_id, price, freight_value
        """
        items = self.data['order_items'].copy()
        result=items.groupby('order_id')[["price","freight_value"]].sum().reset_index()
        return result

    # Optional
    def get_distance_seller_customer(self):
        """
        Returns a DataFrame with:
        order_id, distance_seller_customer
        """
                # $CHALLENGIFY_BEGIN

        # import data
        data = self.data
        orders = data['orders']
        order_items = data['order_items']
        sellers = data['sellers']
        customers = data['customers']

        # Since one zip code can map to multiple (lat, lng), take the first one
        geo = data['geolocation']
        geo = geo.groupby('geolocation_zip_code_prefix',
                          as_index=False).first()

        # Merge geo_location for sellers
        sellers_mask_columns = [
            'seller_id', 'seller_zip_code_prefix', 'geolocation_lat', 'geolocation_lng'
        ]

        sellers_geo = sellers.merge(
            geo,
            how='left',
            left_on='seller_zip_code_prefix',
            right_on='geolocation_zip_code_prefix')[sellers_mask_columns]

        # Merge geo_location for customers
        customers_mask_columns = ['customer_id', 'customer_zip_code_prefix', 'geolocation_lat', 'geolocation_lng']

        customers_geo = customers.merge(
            geo,
            how='left',
            left_on='customer_zip_code_prefix',
            right_on='geolocation_zip_code_prefix')[customers_mask_columns]

        # Match customers with sellers in one table
        customers_sellers = customers.merge(orders, on='customer_id')\
            .merge(order_items, on='order_id')\
            .merge(sellers, on='seller_id')\
            [['order_id', 'customer_id','customer_zip_code_prefix', 'seller_id', 'seller_zip_code_prefix']]

        # Add the geoloc
        matching_geo = customers_sellers.merge(sellers_geo,
                                            on='seller_id')\
            .merge(customers_geo,
                   on='customer_id',
                   suffixes=('_seller',
                             '_customer'))
        # Remove na()
        matching_geo = matching_geo.dropna()

        matching_geo.loc[:, 'distance_seller_customer'] =\
            matching_geo.apply(lambda row:
                               haversine_distance(row['geolocation_lng_seller'],
                                                  row['geolocation_lat_seller'],
                                                  row['geolocation_lng_customer'],
                                                  row['geolocation_lat_customer']),
                               axis=1)
        # Since an order can have multiple sellers,
        # return the average of the distance per order
        order_distance =\
            matching_geo.groupby('order_id',
                                 as_index=False).agg({'distance_seller_customer':
                                                      'mean'})

        return order_distance
 


    def get_training_data(self, is_delivered=True, with_distance_seller_customer=False):
        """
        Returns a clean DataFrame (without NaN), with the all following columns:
        ['order_id', 'wait_time', 'expected_wait_time', 'delay_vs_expected',
        'order_status', 'dim_is_five_star', 'dim_is_one_star', 'review_score',
        'number_of_items', 'number_of_sellers', 'price', 'freight_value',
        'distance_seller_customer']
        """
        # Join all data on 'order_id'
        df = self.get_wait_time(is_delivered=True) \
            .merge(self.get_review_score(), on='order_id') \
            .merge(self.get_number_items(), on='order_id') \
            .merge(self.get_number_sellers(), on='order_id') \
            .merge(self.get_price_and_freight(), on='order_id')


        # Drop rows with missing values
        df = df.dropna()

        return df