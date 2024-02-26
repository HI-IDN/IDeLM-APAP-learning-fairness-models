"""
This module contains the main function for the doctor scheduling tool.

It includes the main function which fetches the data, applies the scheduling algorithm,
outputs the results, and handles any errors that occur during these processes.

The scheduling algorithm is implemented in the AllocationModel class from the allocation_model
module.

This module is intended to be run as a script. It uses command-line arguments to specify the input
and output files, as well as optional parameters such as a requests file and a time limit for the
scheduling process.
"""
import argparse
import logging
import os

from gurobipy import GRB  # pylint: disable=no-name-in-module

from models.allocation_model import AllocationModel
from data.schedule import DoctorSchedule


def main(arguments):
    """
    The main function for the doctor scheduling tool.

    This function fetches the data, applies the scheduling algorithm, outputs the results,
    and handles any errors that occur during these processes.

    Args:
        args (argparse.Namespace): Command-line arguments that specify the input and output files,
                                   as well as optional parameters such as a requests file and a
                                   time limit for the scheduling process.

    Returns:
        None
    """

    # Set up logging
    logfile = arguments.output_filename.replace(".json", ".log")

    if os.path.exists(logfile):
        os.remove(logfile)
    logging.basicConfig(filename=logfile, level=logging.INFO)
    logging.info("Starting the scheduling process...")

    # Step 1: Fetch the data
    try:
        data = DoctorSchedule(args.input_filename)
        logging.info("Data fetched successfully from %s", args.input_filename)
        valid, errors = data.validate()
        assert valid, f"Errors found in schedule: {errors}" + "\n" + data.print()
        data.load_requirements(args.requests)
        valid, errors = data.validate()
        assert valid, (f"Errors found after loading requirements in schedule: {errors}\n" +
                       data.print())
    except Exception as e:
        logging.error("Error while fetching data: %s", e)
        raise ValueError(f"Error while fetching data: {e}") from e

    # Step 2: Apply the scheduling algorithm
    logging.info("Setting up the scheduling model")
    model = AllocationModel(data)
    model.m.setParam('OutputFlag', 0)  # No output from the solver
    model.m.setParam(GRB.Param.TimeLimit,
                     args.time_limit)  # set the time limit to 60 seconds (1 minute)

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
    if os.path.exists(logfile) and model.m.status == GRB.OPTIMAL:
        os.remove(logfile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Doctor Scheduling Tool")
    parser.add_argument("input_filename", type=str, help="Input filename in JSON format")
    parser.add_argument("output_filename", type=str, help="Output filename in JSON format")
    parser.add_argument('-r', '--requests', type=str,
                        help='Requests file to save processed schedule.')
    parser.add_argument('--time_limit', type=int, default=60,
                        help='Time limit for the process in seconds. Default is 60 seconds.')

    args = parser.parse_args()

    main(args)
