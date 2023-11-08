setwd("C://Users/hbi3/Downloads")
library(tidyverse)
library(DBI)
library(RSQLite)
db_file = 'database.sqlite'
file.exists(db_file)
## connect to db
con <- dbConnect(drv = RSQLite::SQLite(), dbname = db_file)

## list all tables
tables <- dbListTables(con)
print(tables)

doctors <- dbReadTable(con, "doctors")
points <- dbGetQuery(con, "
  SELECT p.*, period_start, workdays, target_value
  FROM points p
  INNER JOIN schedule ON schedule.id = p.schedule_id
  ") %>%
  mutate(
    period_start = as.Date(period_start)
  ) %>%
  mutate(regular_week = workdays == 5)
schedule <- dbReadTable(con, "schedule") %>%
  mutate(
    period_start = as.Date(period_start),
    period_end = as.Date(period_end)
  )

dbDisconnect(con)

schedule %>%
  ggplot(aes(x = period_start, y = target_value, color = as.factor(workdays))) +
  geom_point() +
  geom_smooth(method = 'lm', formula = 'y~1', se = FALSE) +
  geom_label(
    data = schedule %>%
      group_by(workdays) %>%
      summarise(period_start = min(period_start),
                target_value = mean(target_value),
                label = sprintf("%.2f", target_value)
      ), aes(label = label)) +
  theme_minimal() +
  xlab(NULL)

points %>% glimpse()
points %>%
  ggplot(aes(x = period_start)) +
  geom_boxplot(aes(group = period_start, y = total_points)) +
  geom_point(aes(y = target_value), color = 'red') +
  geom_smooth(aes(y = target_value), color = 'red', method = 'lm') +
  xlab(NULL) +
  facet_grid(regular_week ~ .)

points %>%
  mutate(off_target = total_points - target_value) %>%
  ggplot(aes(x = period_start)) +
  geom_point(aes(group = period_start, y = off_target, color = abs(off_target))) +
  xlab(NULL) +
  facet_grid(regular_week ~ .)

