# Locations and patterns
QUARTERLY_DATA=../data/quarterly_data
WEEKLY_CALL_DATA=../data/weekly_call_data
WEEKLY_UNASSIGNED_DATA=../data/weekly_unassigned_data
WEEKLY_ASSIGNED_DATA=../data/weekly_assigned_data

QUARTER_XLS=$(wildcard $(QUARTERLY_DATA)/*.xls)
QUARTER_JSON=$(subst .xls,.json,$(QUARTER_XLS))
WEEKLY_JSON_ALL = $(sort $(notdir $(wildcard $(WEEKLY_CALL_DATA)/[0-9][0-9][0-9][0-9]-week[0-9][0-9].json)))
FIRST_WEEKLY_JSON = $(firstword $(WEEKLY_JSON_ALL))
LAST_WEEKLY_JSON = $(lastword $(WEEKLY_JSON_ALL))
WEEKLY_JSON = $(filter-out $(FIRST_WEEKLY_JSON) $(LAST_WEEKLY_JSON),$(WEEKLY_JSON_ALL))


# Convert .xls to .json
$(QUARTERLY_DATA)/%.json: $(QUARTERLY_DATA)/%.xls data/xls_to_json_converter.py ../data/staff.csv
	python3 data/xls_to_json_converter.py $< -o $@ --simple

# Split quarterly .json into weekly segments
$(WEEKLY_CALL_DATA): data/quarterly_json_week_splitter.py $(QUARTER_JSON)
	mkdir $@.tmp
	$(foreach q,$(QUARTER_JSON),python3 data/quarterly_json_week_splitter.py $(q) --outdir $@.tmp || exit 1;)
	rm -rf $@ && mv $@.tmp $@

# Derive unassigned weekly plans from the weekly call plans
$(WEEKLY_UNASSIGNED_DATA)/%.json: $(WEEKLY_CALL_DATA)/%.json data/derive_shifts_from_schedule.py
	python3 data/derive_shifts_from_schedule.py -i $< -o $@

# Generate the solved/assigned plans
$(WEEKLY_ASSIGNED_DATA)/%.json: $(WEEKLY_UNASSIGNED_DATA)/%.json schedule_optimizer.py
	python3 schedule_optimizer.py $< $@

unassigned: $(foreach w,$(WEEKLY_JSON),$(WEEKLY_CALL_DATA)/$(w))
	rm -rf $(WEEKLY_UNASSIGNED_DATA) && mkdir $(WEEKLY_UNASSIGNED_DATA)
	make $(foreach w,$(WEEKLY_JSON),$(WEEKLY_UNASSIGNED_DATA)/$(w))

assigned: $(foreach w,$(WEEKLY_JSON),$(WEEKLY_UNASSIGNED_DATA)/$(w))
	make $(foreach w,$(WEEKLY_JSON),$(WEEKLY_ASSIGNED_DATA)/$(w))

# Default target
all:
	make $(QUARTER_JSON)
	make $(WEEKLY_CALL_DATA)
	make unassigned
	make assigned