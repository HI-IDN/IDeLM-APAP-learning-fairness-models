setwd("C://Users/hbi3/Downloads")
library(tidyverse)
theme_set(theme_minimal())

create_mainplot_with_marginals <- function(main_plot, x_marginal_plot, y_marginal_plot){
  # Ensure that the marginal plots don't have any axes or strip text
  x_marginal_plot <- x_marginal_plot + theme(
    axis.title.x = element_blank(),
    #axis.text.x = element_blank(),
    axis.ticks.x = element_blank(),
    plot.margin = margin(0,0,0,0)
  )
  
  y_marginal_plot <- y_marginal_plot + theme(
    axis.title.y = element_blank(),
    #axis.text.y = element_blank(),
    axis.ticks.y = element_blank(),
    plot.margin = margin(0,0,0,0)
  )
  
  # Align the plots and assemble them
  combined_plot <- x_marginal_plot +
    patchwork::plot_layout(widths = c(4, 1), heights = c(1, 4)) +
    patchwork::plot_spacer()+ 
    main_plot + 
    y_marginal_plot
  
  # Print the combined plot
  combined_plot
}


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
                                        'Neither')
                          )))

  points <- dbReadTable(con, "points") %>%
    mutate(
      mean_daily_pts = total_points/days_working
    )
  
  schedule <- dbReadTable(con, "schedule") %>%
    mutate(
      period_start = as.Date(period_start),
      period_end = as.Date(period_end), 
      regular_week = workdays==5
    )
  
  assignments <- dbReadTable(con, "assignments") %>% 
    group_by(date) %>% mutate(
      date = as.Date(date),
      n_working=n(),
      points = as.numeric(points)
      ) %>% 
    ungroup()
  
  holidays <- dbReadTable(con, "holidays") %>% 
    mutate(date = as.Date(date))

  dbDisconnect(con)

  return(list(
    doctors = doctors,
    points = points,
    schedule = schedule,
    assignments = assignments,
    holidays = holidays
  ))
}

# Check if data is already loaded
print("Loading data")
db <- read_database()


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
  xlab(NULL)

db$points %>% 
  merge(db$schedule %>% select(id, period_start, target_value, regular_week), 
        by.x='schedule_id', by.y='id') %>%
  filter(target_value < 20) %>% 
  ggplot(aes(x = period_start)) +
  geom_boxplot(aes(group = period_start, y = total_points/days_working)) +
  geom_point(aes(y = target_value), color = 'red') +
  geom_smooth(aes(y = target_value), color = 'red', method='lm') +
  xlab(NULL)

db$points %>%
  merge(db$schedule %>% select(id, period_start, target_value), 
        by.x='schedule_id', by.y='id') %>%
  mutate(off_target = total_points/days_working - target_value) %>%
  ggplot(aes(x = period_start)) +
  geom_point(aes(group = period_start, y = off_target, color = abs(off_target))) +
  xlab(NULL)

db$schedule %>%
  group_by(workdays) %>%
  tally() %>%
  print()

# Calculate the means, merge back with the full data, and then plot
cowplot::plot_grid(
db$points %>%
  left_join(db$doctors, by = c("doctor_id" = "id")) %>%
  ggplot(aes(x = reorder(doctor_id, -total_points, FUN = mean), y = total_points, fill = roles)) +
  geom_boxplot() +
  xlab(NULL) +
  theme(axis.text.x = element_text(angle = 90, hjust = 1)) # Rotate x labels for readability
,
db$points %>%
  left_join(db$doctors, by = c("doctor_id" = "id")) %>%
  ggplot(aes(x = reorder(doctor_id, -total_points, FUN = mean), y = total_points/days_working, fill = roles)) +
  geom_boxplot() +
  xlab(NULL) +
  theme(axis.text.x = element_text(angle = 90, hjust = 1)) # Rotate x labels for readability
,nrow=2)


# Plot the cumulative points for each doctor over time 
db$points %>% 
  merge(db$schedule %>% select(id, period_start), by.x='schedule_id', by.y='id') %>%
  arrange(period_start) %>% 
  group_by(doctor_id) %>% mutate(cumulative_points = cumsum(total_points)) %>%
  ungroup() %>%
  ggplot(aes(x = period_start, y = cumulative_points, group = doctor_id, color = doctor_id)) +
  geom_line() +
  labs(x = NULL, y = "Cumulative Total Points", color = "Doctor ID") 

db$points %>% 
  merge(db$schedule %>% select(id, period_start), by.x='schedule_id', by.y='id') %>%
  arrange(period_start) %>% 
  group_by(doctor_id) %>%
  mutate(
    cumulative_points = cumsum(total_points),
    cumulative_workdays = cumsum(days_working)
  ) %>%
  ungroup() %>%
  ggplot(aes(x = period_start, y = cumulative_points / cumulative_workdays, group = doctor_id, color = doctor_id)) +
  geom_line() +
    labs(
    x = "Period Start Date",
    title= "Normalized Points per Week",
    color = "Doctor ID"
  )

# Summarize the data
summary_data <- db$assignments %>%
  group_by(doctor_id) %>%
  summarise(
    n_charge = sum(is_charge),
    n_cardiac = sum(is_cardiac),
    n = n(), 
    working_weekends = sum(n_working == 2),
    working_weekdays = sum(n_working > 2)
  )

# Create a long format data frame for plotting
long_data <- summary_data %>%
  gather(key = "Working", value = "count", working_weekends, working_weekdays) %>%
  mutate(Working = factor(Working, levels = c("working_weekdays", "working_weekends"), labels = c("Weekdays", "Weekends \n& Holidays")))

# Plot
ggplot(long_data, aes(x = reorder(doctor_id, -n), y = count, fill = Working)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = ifelse(Working == "Weekdays", '', count), y = count), vjust = -0.5) +
  labs(x = NULL, y = "Count") 

heatmap <- function(assignments){
  
  # Create a factor for doctor_id with levels ordered by the sum of values
  ordered_doctor_ids <- assignments %>% 
    group_by(doctor_id) %>% 
    summarise(total_value = sum(points)) %>% 
    arrange(desc(total_value)) %>% 
    .$doctor_id
  
  # Convert doctor_id to a factor in the original data frame with the new level order
  assignments$doctor_id <- factor(assignments$doctor_id, levels = ordered_doctor_ids)
  
  heatmap_plot <- assignments %>% 
    group_by(doctor_id, points) %>% 
    summarise(value = n()) %>% 
    ggplot(aes(x = doctor_id, y = points, fill = value)) + 
    geom_tile(color = "black") +
    geom_text(aes(label = value), color = "white", size = 4) +
    viridis::scale_fill_viridis()+
    guides(fill = guide_colourbar(barwidth = 17, title='Count'))+
    labs(x='',y='Point Position')+
    theme(legend.position = 'bottom')

  # Plot for distribution of doctor_id (X-axis)
  x_dist_plot <- assignments %>% 
    count(doctor_id) %>% 
    ggplot(aes(x = doctor_id, y = n)) +
    geom_bar(stat = "identity") +
    scale_x_discrete(limits = ordered_doctor_ids) # Order x-axis according to the factor
    
  # Plot for distribution of points (Y-axis)
  y_dist_plot <- assignments %>% 
    count(points) %>% 
    ggplot(aes(x = points, y = n)) +
    geom_bar(stat = "identity") +
    coord_flip()

  # Combine the plots
  create_mainplot_with_marginals(heatmap_plot, x_dist_plot, y_dist_plot)
  
}
heatmap(db$assignments %>% filter(n_working>2))
heatmap(db$assignments %>% filter(n_working==2))
  

plot_objective <- function(db_schedule){
  # Reshape the data to long format
  long_data <- db_schedule %>% 
    pivot_longer(cols = c(target_value, objective_total, objective_equity, objective_cardiac_charge, objective_priority_charge), 
                 names_to = "Objective", 
                 values_to = "Value")
  
  # Create the facet plot
  ggplot(long_data, aes(x = period_start, y = Value)) + 
    geom_point() + 
    facet_wrap(~ Objective, scales = "free_y") +
    theme_minimal() +
    labs(title = "Objective Analysis Over Time", x = "Period Start", y = "Value")
}
plot_objective(db$schedule)


# Create the bar plot with reordered doctor_id
db$assignments %>% filter(n_working==2) %>%
  left_join(db$holidays, by='date') %>%
  mutate(
    weekday=lubridate::wday(date,label = TRUE, locale = "en_US"),
    holiday = !(is.na(description)),
    description = coalesce(description,weekday)
    ) %>% 
  ggplot(aes(x = doctor_id, fill = description)) +
  geom_histogram(stat='count')+
  xlab(NULL) 
