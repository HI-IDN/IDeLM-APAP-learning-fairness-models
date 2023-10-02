# README: Anesthesia Scheduling Equity Problem
## Overview:
The Anesthesia Scheduling Equity Problem (ASEP) addresses unique challenges faced by anesthesiologists in their 
daily scheduling. Given the unpredictable nature of their operations, there is a need to ensure an equitable 
distribution of workload.

## Background: 
Background:
Anesthesiologists operate differently from many other professions, especially when it comes to daily scheduling:

Their day often starts before 7:00 am and can vary greatly in length.

The exact end of the workday is unpredictable due to varying surgery schedules and procedure durations.

There isn't a fixed *end-of-the-day*; instead, anesthesiologists might leave at different times as their services 
are no longer required.

## Operational Details:
The anesthesiologist group comprises 22 consultants working across three primary locations:

### Outpatient Surgical Clinic (Childrens Minnetonka, West):
* Operates during daytime hours.
* Services minor surgeries.
* No evening or overnight services.
### Gillette Children´s Speciality Hospital:
* Offers 24/7 coverage.
* Serves patients needing advanced orthopedic care, rehabilitation, neurosurgery, and plastic surgery.
* Consistently has a team of 3-4 anesthesiologists with one on overnight duty.
### Children’s Minnesota Hospital:
* Largest service area with multiple specialties.
* On an average day, requires 11-13 anesthesiologists.
* Two anesthesiologists are always on call.
* One stays overnight ("call anesthesiologist") and another works late ("late-call anesthesiologist").

## Special Considerations:

* Specialized Heart Surgery Services: Half of the anesthesiology team specializes in cardiac surgeries. One from this 
group is always in either the call or late-call role.
* OR Management / Charge Doctor: A designated doctor oversees the operations of the hospital's operating rooms. This 
  role often requires extended hours.
* CVCC (Cardiovascular Critical Care): One anesthesiologist serves in the cardiac ICU. After an overnight ICU shift, 
  this doctor departs first the following day.
* Non-clinical: 4-5 of the six anesthesiologists not working daily are on vacation, and 1-2 are allocated for 
  administrative duties.

## Objective:
Develop a model to equitably assign work to the 6-7 anesthesiologists who have varying tasks each working weekday.


## Getting Started
### Prerequisites:
* Google Cloud authentication to access Google Sheets.
* Installation of packages listed in `requirements.txt` and the necessary authentication modules: 
   ```pip install -r requirements.txt ```

### Execution:
* Input the Google Sheets ID and Sheet name.
* Ensure that the Google Sheets data format matches the expected layout.
* Execute the code. Upon completion, assignments will be stored in the variable `x`.