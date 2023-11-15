import argparse
import logging

from data.schedule import DoctorSchedule
from models.allocation_model import AllocationModel

import os


def main(args):
    # Set up logging
    logfile = args.output_filename.replace(".json", ".log")

    if os.path.exists(logfile):
        os.remove(logfile)
    logging.basicConfig(filename=logfile, level=logging.INFO)
    logging.info("Starting the scheduling process...")

    # Step 1: Fetch the data
    try:
        data = DoctorSchedule(args.input_filename)
        logging.info(f"Data fetched successfully from {args.input_filename}")
        valid, errors = data.validate()
        assert valid, f"Errors found in schedule: {errors}" + "\n" + data.print()
        data.load_requirements(args.requests)
        valid, errors = data.validate()
        assert valid, f"Errors found after loading requirements in schedule: {errors}" + "\n" + data.print()
    except Exception as e:
        logging.error(f"Error while fetching data: {e}")
        raise ValueError(f"Error while fetching data: {e}")

    # Step 2: Apply the scheduling algorithm
    logging.info("Setting up the scheduling model, with the following parameters: simple={args.simple}")
    model = AllocationModel(data, simple=args.simple)
    model.m.setParam('OutputFlag', 0)  # No output from the solver

    if not model.solve():
        # Step 3: If no solution is found, print the constraints
        print("No solution found")
        model.print()
        model.print(logfile)
        model.debug_constraints()
        return

    # Step 4: Output the results
    model.print()
    model.print(logfile)
    model.save(args.output_filename)
    logging.info("Scheduling process completed successfully")
    if os.path.exists(logfile):
        os.remove(logfile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Doctor Scheduling Tool")
    parser.add_argument("input_filename", type=str, help="Input filename in JSON format")
    parser.add_argument("output_filename", type=str, help="Output filename in JSON format")
    parser.add_argument('-r', '--requests', type=str, help='Requests file to save processed schedule.')
    parser.add_argument("--simple", action="store_true", help="Use the simple model")
    args = parser.parse_args()

    main(args)
