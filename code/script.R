setwd("C://Users/hbi3/Downloads")
library(tidyverse)

read_database <- function(db_file = 'database.sqlite') {
  library(DBI)
  library(RSQLite)
  if (!file.exists(db_file)) {
    stop("Database file not found")
  }

  print("Connecting to database")
  con <- dbConnect(drv = RSQLite::SQLite(), dbname = db_file)

  print("Reading tables")
  tables <- dbListTables(con)
  print(tables)

  doctors <- dbReadTable(con, "doctors") %>%
    mutate(roles = ifelse(cardiac & charge, 'Both',
                          ifelse(cardiac, 'Cardiac',
                                 ifelse(charge, 'Charge',
                                        'None')
                          )))

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

  return(list(
    doctors = doctors,
    points = points,
    schedule = schedule
  ))
}

# Check if data is already loaded
if (!exists("db")) {
  print("Loading data")
  db <- read_database()
}


db$schedule %>%
  ggplot(aes(x = period_start, y = target_value, color = as.factor(workdays))) +
  geom_point() +
  geom_smooth(method = 'lm', formula = 'y~1', se = FALSE) +
  geom_label(
    data = db$schedule %>%
      group_by(workdays) %>%
      summarise(period_start = min(period_start),
                target_value = mean(target_value),
                label = sprintf("%.2f", target_value)
      ), aes(label = label)) +
  theme_minimal() +
  xlab(NULL)

db$points %>%
  ggplot(aes(x = period_start)) +
  geom_boxplot(aes(group = period_start, y = total_points)) +
  geom_point(aes(y = target_value), color = 'red') +
  geom_smooth(aes(y = target_value), color = 'red', method = 'lm') +
  xlab(NULL) +
  facet_grid(regular_week ~ .)

db$points %>%
  mutate(off_target = total_points - target_value) %>%
  ggplot(aes(x = period_start)) +
  geom_point(aes(group = period_start, y = off_target, color = abs(off_target))) +
  xlab(NULL) +
  facet_grid(regular_week ~ .)

db$schedule %>%
  group_by(workdays) %>%
  tally() %>%
  print()

# Calculate the means, merge back with the full data, and then plot
db$points %>%
  left_join(db$doctors, by = c("doctor_id" = "id")) %>%
  ggplot(aes(x = reorder(doctor_id, -total_points, FUN = mean), y = total_points, fill = roles)) +
  geom_boxplot() +
  xlab(NULL) +
  theme(axis.text.x = element_text(angle = 90, hjust = 1)) # Rotate x labels for readability

# Plot the cumulative points for each doctor over time 
db$points %>% 
  group_by(doctor_id) %>% mutate(cumulative_points = cumsum(total_points)) %>%
  ungroup() %>%
  ggplot(aes(x = period_start, y = cumulative_points, group = doctor_id, color = doctor_id)) +
  geom_line() +
  labs(x = NULL, y = "Cumulative Total Points", color = "Doctor ID") +
  theme_minimal()

standard_workweek_days <- 5 # 5 days workweek
db$points %>%
  group_by(doctor_id) %>%
  mutate(
    cumulative_points = cumsum(total_points),
    cumulative_workdays = cumsum(workdays),
    points_per_week = (cumulative_points / cumulative_workdays) * standard_workweek_days # Normalize
  ) %>%
  ungroup() %>%
  ggplot(aes(x = period_start, y = points_per_week, group = doctor_id, color = doctor_id)) +
  geom_line() +
    labs(
    x = "Period Start Date",
    y = paste(standard_workweek_days,"x cumulative points / cumulative workdays"),
    title= "Normalized Points per Week",
    color = "Doctor ID"
  ) +
  theme_minimal()
  
