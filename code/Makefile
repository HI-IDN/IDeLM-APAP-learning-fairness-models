# Locations and patterns
QUARTERLY_DATA=../data/quarterly_data
WEEKLY_CALL_DATA=../data/weekly_call_data
WEEKLY_UNASSIGNED_DATA=../data/weekly_unassigned_data
WEEKLY_ASSIGNED_DATA=../data/weekly_assigned_data
WEEKLY_REQUEST_DATA=../data/weekly_request_data

QUARTER_XLS=$(wildcard $(QUARTERLY_DATA)/*.xls)
QUARTER_JSON=$(subst .xls,.json,$(QUARTER_XLS))
WEEKLY_JSON_ALL = $(sort $(notdir $(wildcard $(WEEKLY_CALL_DATA)/[0-9][0-9][0-9][0-9]-week[0-9][0-9].json)))
FIRST_WEEKLY_JSON = $(firstword $(WEEKLY_JSON_ALL))
LAST_WEEKLY_JSON = $(lastword $(WEEKLY_JSON_ALL))
WEEKLY_JSON = $(filter-out $(FIRST_WEEKLY_JSON) $(LAST_WEEKLY_JSON),$(WEEKLY_JSON_ALL))
UNASSIGNED_JSON = $(notdir $(filter-out %_ILLEGAL.json, $(wildcard $(WEEKLY_UNASSIGNED_DATA)/*.json)))
DB_FILE = $(WEEKLY_ASSIGNED_DATA)/database.sqlite

# Convert .xls to .json
$(QUARTERLY_DATA)/%.json: $(QUARTERLY_DATA)/%.xls data/xls_to_json_converter.py ../data/staff.csv
	python3 data/xls_to_json_converter.py $< -o $@ --simple

# Split quarterly .json into weekly segments
$(WEEKLY_CALL_DATA): data/quarterly_json_week_splitter.py $(QUARTER_JSON)
	mkdir $@.tmp
	$(foreach q,$(QUARTER_JSON),python3 -m data.quarterly_json_week_splitter $(q) --outdir $@.tmp || exit 1;)
	rm -rf $@ && mv $@.tmp $@

# Derive unassigned weekly plans from the weekly call plans
$(WEEKLY_UNASSIGNED_DATA)/%.json: $(WEEKLY_CALL_DATA)/%.json
	python3 -m data.derive_shifts_from_schedule -i $< -o $@ -r $(WEEKLY_REQUEST_DATA)/$(notdir $@)

# Generate the solved/assigned plans
$(WEEKLY_ASSIGNED_DATA)/%.json: $(WEEKLY_UNASSIGNED_DATA)/%.json $(WEEKLY_REQUEST_DATA)/%.json models/schedule_optimizer.py
	python3 -m models.schedule_optimizer $< $@ -r $(word 2,$^)

quarterly:
	make $(QUARTER_JSON)

weekly:
	make $(WEEKLY_CALL_DATA)

unassigned: $(foreach w,$(WEEKLY_JSON),$(WEEKLY_CALL_DATA)/$(w))
	make $(foreach w,$(WEEKLY_JSON),$(WEEKLY_UNASSIGNED_DATA)/$(w))

assigned:
	make $(foreach w,$(UNASSIGNED_JSON),$(WEEKLY_ASSIGNED_DATA)/$(w))

.PHONY: import
import:
	@echo "Importing JSON files from $(WEEKLY_ASSIGNED_DATA) into $(DB_FILE):"
	python3 import_json_to_sqlite.py "$(DB_FILE)" $(WEEKLY_ASSIGNED_DATA)
	cp $(DB_FILE) /mnt/c/Users/hbi3/Downloads/$(notdir $(DB_FILE))

clean:
	@echo Removing quarterly JSON files
	rm -f $(QUARTERLY_DATA)/[1-2][0-9][0-9][0-9]_[1-4]q.json
	@echo Removing weekly call data
	rm -rf $(WEEKLY_CALL_DATA)/
	@echo Removing unassigned JSON files
	rm -f $(WEEKLY_UNASSIGNED_DATA)/[1-2][0-9][0-9][0-9]-week[0-5][0-9].json
	@echo Removing assigned JSON files
	rm -f $(WEEKLY_ASSIGNED_DATA)/[1-2][0-9][0-9][0-9]-week[0-5][0-9].json
	rm -f $(WEEKLY_ASSIGNED_DATA)/*.err $(WEEKLY_ASSIGNED_DATA)/*.log
	@echo Remove any placeholder requests
	rm -rf $(WEEKLY_REQUEST_DATA)/[1-2][0-9][0-9][0-9]-week[0-5][0-9].json


# Default target
all:
	make quarterly
	make weekly
	make unassigned
	make assigned
	make import
