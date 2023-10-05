# Define locations and patterns
QUARTER_CALL_PLAN=../data/quarterly_plans
WEEKLY_CALL_PLANS=../data/weekly_call_plans
WEEKLY_PLANS=../data/weekly_plans

QUARTER_XLS=$(wildcard $(QUARTER_CALL_PLAN)/*.xls)
QUARTER_JSON=$(subst .xls,.json,$(QUARTER_XLS))
WEEKLY_CALL_JSON=$(wildcard $(WEEKLY_CALL_PLANS)/*.json)


# Rule to convert .xls to .json
$(QUARTER_CALL_PLAN)/%.json: $(QUARTER_CALL_PLAN)/%.xls data/xls_to_json_converter.py ../data/staff.csv
	python3 data/xls_to_json_converter.py $< -o $@ --simple

# Rule to split quarterly .json into weekly segments
$(WEEKLY_CALL_PLANS): data/quarterly_json_week_splitter.py $(QUARTER_JSON)
	rm -rf $@.tmp && mkdir $@.tmp
	$(foreach q,$(QUARTER_JSON),python3 data/quarterly_json_week_splitter.py $(q) --outdir $@.tmp  || exit 1;)
	mv $@.tmp $@

# This intermediate rule will ensure that each JSON file gets generated in the temporary directory.
$(WEEKLY_PLANS).tmp/%.json: $(WEEKLY_CALL_PLANS)/%.json data/derive_shifts_from_schedule.py
	python3 data/derive_shifts_from_schedule.py -i $< -o $@

# This is a 'phony' target which means it's not associated with any actual file, just a name for a set of instructions.
.INTERMEDIATE: move-weekly-json-files-to-tmp

# Sort the list and store in a temporary variable.
SORTED_WEEKLY_CALL_JSON := $(sort $(WEEKLY_CALL_JSON))

# Remove the first and last item from the sorted list.
ifneq ($(words $(SORTED_WEEKLY_CALL_JSON)),0)
FIRST_WEEK := $(firstword $(SORTED_WEEKLY_CALL_JSON))
LAST_WEEK  := $(word $(words $(SORTED_WEEKLY_CALL_JSON)),$(SORTED_WEEKLY_CALL_JSON))
ADJUSTED_WEEKLY_CALL_JSON := $(filter-out $(FIRST_WEEK) $(LAST_WEEK),$(SORTED_WEEKLY_CALL_JSON))
else
ADJUSTED_WEEKLY_CALL_JSON :=
endif

move-weekly-json-files-to-tmp:
	mkdir -p $(WEEKLY_PLANS).tmp && find $(WEEKLY_PLANS).tmp -type f -delete
	$(foreach w,$(ADJUSTED_WEEKLY_CALL_JSON), make $(subst $(WEEKLY_CALL_PLANS),$(WEEKLY_PLANS).tmp,$(w)) || exit 1;)

# This is your main target to move the processed files from temp to the main directory.
$(WEEKLY_PLANS): move-weekly-json-files-to-tmp
	mv $(WEEKLY_PLANS).tmp/* $(WEEKLY_PLANS)/
	rmdir $(WEEKLY_PLANS).tmp


# Default target
all:
	make $(QUARTER_JSON)
	make $(WEEKLY_CALL_PLANS)
tmp:
	make $(WEEKLY_PLANS)

