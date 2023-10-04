from data.data_handler import DataHandler
from models.allocation_model import AllocationModel


def main():
    # Constants

    # Step 1: Fetch the data
    df = DataHandler('data/input.csv')

    # Step 2: Preprocess the data (if needed)
    # df = some_preprocessing_function(df)

    # Step 3: Apply the scheduling algorithm
    model = AllocationModel(df, simple=False)
    if not model.solve():
        print("No solution found")
        model.debug_constraints()
        return

    # Step 4: Output the results
    model.print()


if __name__ == '__main__':
    main()
