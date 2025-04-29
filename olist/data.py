import os
import pandas as pd


class Olist:
    def get_data(self):
        """
        This function returns a Python dict.
        Its keys should be 'sellers', 'orders', 'order_items' etc...
        Its values should be pandas.DataFrames loaded from csv files
        """
         # Get the absolute path of the current file (data.py)
        current_file_path = os.path.abspath(__file__)

        # Get the directory containing the current file
        current_dir = os.path.dirname(current_file_path)

        # Go up one level to the main project directory
        project_dir = os.path.dirname(current_dir)

        # Construct the path to the csv directory
        csv_path = os.path.join(project_dir, 'data', 'csv')

        # Create the list of file names containing only CSV files
        file_names = [file for file in os.listdir(csv_path) if file.endswith('.csv')]

        # Create the list of dict keys by cleaning the file names
        key_names = []
        for file in file_names:
            # Remove suffix and prefix according to the rules
            key = file
            if key.endswith('_dataset.csv'):
                key = key.replace('_dataset.csv', '')
            elif key.endswith('.csv'):
                key = key.replace('.csv', '')

            if key.startswith('olist_'):
                key = key[6:]  # Remove 'olist_' prefix

            key_names.append(key)

        # Construct the dictionary of DataFrames
        data = {}
        for key, file in zip(key_names, file_names):
            file_path = os.path.join(csv_path, file)
            data[key] = pd.read_csv(file_path)

        return data


    def ping(self):
        """
        You call ping I print pong.
        """
        print("pong")
