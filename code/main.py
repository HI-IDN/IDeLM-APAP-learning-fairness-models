from data.schedule import DoctorSchedule
from models.allocation_model import AllocationModel


def main():
    # Constants

    # Step 1: Fetch the data
    data = DoctorSchedule('data/input.json')

    # Step 2: Apply the scheduling algorithm
    model = AllocationModel(data, simple=False)
    if not model.solve():
        print("No solution found")
        model.debug_constraints()
        return

    # Step 4: Output the results
    model.print()


if __name__ == '__main__':
    main()
