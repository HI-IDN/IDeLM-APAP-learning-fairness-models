import argparse
import logging
from data.schedule import DoctorSchedule
from models.allocation_model import AllocationModel


def main(args):
    # Set up logging
    logging.basicConfig(filename=args.output_filename.replace(".json", ".log"),
                        level=logging.INFO)

    logging.info("Starting the scheduling process...")

    # Step 1: Fetch the data
    try:
        data = DoctorSchedule(args.input_filename)
    except Exception as e:
        logging.error(f"Error while fetching data: {e}")
        return

    # Step 2: Apply the scheduling algorithm
    model = AllocationModel(data, simple=False)
    if not model.solve():
        # Step 3: If no solution is found, print the constraints
        logging.error("No solution found")
        model.debug_constraints()
        return

    # Step 4: Output the results
    model.print()
    logging.info("Scheduling process completed successfully")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Doctor Scheduling Tool")
    parser.add_argument("input_filename", type=str, help="Input filename in JSON format")
    parser.add_argument("output_filename", type=str, help="Output filename in JSON format")
    args = parser.parse_args()

    main(args)
