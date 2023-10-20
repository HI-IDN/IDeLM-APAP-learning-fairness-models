import csv
import datetime
import datetime as dt

ADMIN_IDENTIFIER = 'AD'
ADMIN_IDENTIFIERS = ['AD', 'Admin', 'Adm']
CARDIAC_IDENTIFIER = "\u2764\u205F"  # Heart symbol
CHARGE_IDENTIFIER = "\u2699\u205F"  # Gear symbol


class Doctors:
    """
    A class representing all doctors.
    """

    def __init__(self, file='../data/staff.csv', start_date=None, end_date=None):
        if end_date is None:
            end_date = datetime.date.max
        if start_date is None:
            start_date = datetime.date.today()
        assert end_date >= start_date, "End date must be after start date."
        self.unknown = Doctor('X', 'Placeholder', False, False, [])

        self._doctors = []
        with open(file) as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            for row in reader:
                started = dt.datetime.strptime(row[5], '%Y-%m-%d').date() if row[5] else dt.date.max
                ended = dt.datetime.strptime(row[6], '%Y-%m-%d').date() if row[6] else dt.date.max
                if started > end_date or ended < start_date or started >= ended:
                    continue
                initial = row[0]
                diac = True if row[1] == "TRUE" else False
                charge = True if row[2] == "TRUE" else False
                name = row[3]
                alias = row[4].split(";")
                self._doctors.append(Doctor(initial, name, diac, charge, alias if alias != [''] else []))
        self._everyone = sorted([doc.ID for doc in self._doctors])
        self._cardiac_doctors = [doc.ID for doc in self._doctors if doc.can_be_cardiac]
        self._charge_doctors = [doc.ID for doc in self._doctors if doc.can_be_charge]

    def __str__(self):
        """Returns a string representation of all doctors."""
        return "\n".join([str(doc) for doc in self._doctors])

    def get_name(self, doctor_info):
        """Returns the name of the doctor with the given ID."""
        return [doc.name for doc in self._doctors if doc.ID == doctor_info][0]

    @property
    def cardiac_doctors(self):
        """Returns a list of all doctors who can be cardiac."""
        return self._cardiac_doctors

    @property
    def charge_doctors(self):
        """Returns a list of all doctors who can be charge."""
        return self._charge_doctors

    @property
    def everyone(self):
        """Returns a list of all doctors' initials."""
        return self._everyone

    def find_doctor_identifier(self, doctor_info):
        assert isinstance(doctor_info, str), "Doctor info must be a string."
        doctor_info = doctor_info.strip()  # Remove leading and trailing whitespace
        for doctor in self._doctors + [self.unknown]:  # Otherwise, check if doctor_info is a name
            if doctor_info == doctor.ID or doctor_info == doctor.name or doctor_info in doctor.alias:
                return doctor.ID

        # Return error message if doctor_info is neither an ID nor a name
        assert False, f"Could not find doctor with name or ID '{doctor_info}'."

    def __iter__(self):
        """Returns an iterator over all doctors."""
        return iter(self._doctors)


class Doctor:
    """
    A class representing a doctor.
    """

    def __init__(self, initials, name, cardiac, charge, alias):
        self.name = name
        self.ID = initials
        self.can_be_cardiac = cardiac
        self.can_be_charge = charge
        self.alias = alias

    def __str__(self):
        heart = CARDIAC_IDENTIFIER if self.can_be_cardiac else ""
        gear = CHARGE_IDENTIFIER if self.can_be_charge else ""
        # This will ensure no extra spaces between name, heart, and gear
        return f"{self.ID} {heart}{gear}".strip()


if __name__ == '__main__':
    staff = Doctors()
    print(staff)
    print(f'All doctors (#{len(staff.everyone)}): {", ".join(staff.everyone)}.')
    print(f'Charge doctors (#{len(staff.charge_doctors)}): {", ".join(staff.charge_doctors)}.')
    print(f'Cardiac doctors (#{len(staff.cardiac_doctors)}): {", ".join(staff.cardiac_doctors)}.')
