from data.data_handler import DataHandler
from models.allocation_model import AllocationModel
# from utils import some_utility_function

def main():
    # Constants

    # Step 1: Fetch the data
    df = DataHandler('data/input.csv')

    # Step 2: Preprocess the data (if needed)
    # df = some_preprocessing_function(df)

    # Step 3: Apply the scheduling algorithm
    results = AllocationModel(df)

    # Step 4: Output the results
    # some_utility_function(results)


if __name__ == '__main__':
    main()
