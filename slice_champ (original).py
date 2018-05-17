import pg8000
import pandas as pd
import jem_funcs
from datetime import datetime, timedelta
from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import USFederalHolidayCalendar

def slice_champion(recording_date):
    """Takes a date and returns the rig operator(s) with the most patched cell containers from a slice on that date.
    
    Parameters
    ----------
    recording_date : string
        A date in the format YYMMDD.
    
    Returns
    -------
    string
        A message naming the slice champion(s) for the day.
    """
    
    users = {'P1':'Kristen', 'P2':'Rusty', 'P8':'Lindsay', 'P9':'Lisa', 'PA':'Ram', 'PB':'DiJon'}
    
    recording_date_query_str = "%%" + recording_date + "%%"
    lims_query_str="SELECT cell.parent_id, cell.patched_cell_container \
    FROM specimens cell JOIN projects proj ON cell.project_id = proj.id \
    WHERE proj.code <> 'mMPATCH' AND \
    cell.patched_cell_container IS NOT NULL \
    AND cell.patched_cell_container LIKE '%s'" %recording_date_query_str
    
    containers = pd.DataFrame(jem_funcs.limsquery(lims_query_str))
    if containers.empty:
        return "No patched cells from that date"
    cell_counts = containers.groupby(['parent_id']).size().reset_index(name = 'cells')
    
    most_cells = cell_counts['cells'].max()
    winning_slice = cell_counts[cell_counts['cells'] == most_cells]
    winner = len(winning_slice)
    
    if winner > 1:
        for slice_n in winning_slice.parent_id:
            container_n = containers[containers['parent_id'] == slice_n].patched_cell_container.values[0]
            user_code_n = container_n[0:2]
            user_name_n = users[user_code_n]
            print "%s" %user_name_n + " got %d cells!" %most_cells
        return "Yep, there's a %d way tie!" %winner
    else:
        winning_slice = winning_slice.parent_id.values[0]
        winning_container = containers[containers['parent_id'] == winning_slice].patched_cell_container.values[0]
        user_code = winning_container[0:2]
        user_name = users[user_code]
        return "The winner is %s" %user_name + " with %d cells!" %most_cells

"""------------------------Get last business day---------------"""
bday_us = CustomBusinessDay(calendar=USFederalHolidayCalendar())
last_bday = (datetime.today() - bday_us).date()
last_bday_str = last_bday.strftime("%y%m%d")

"""------------------------Ask for user input----------------"""
str_prompt1 = "\nWould you like to report on recordings from %s? (y / n): "  %last_bday_str
valid_vals = ["y", "n"]
str_prompt2 = "Please enter date to report on (YYMMDD): "

response1 = "\nPlease try again..."
response2 = "\nPlease try again... date should be YYMMDD"

last_bday_state = jem_funcs.validated_input(str_prompt1, response1, valid_vals)
if last_bday_state == "n":
    report_date = jem_funcs.validated_date_input(str_prompt2, response2, valid_options=None)
    report_dt = datetime.strptime(report_date, "%y%m%d") .date()
    comparison_date = report_dt + timedelta(days=1)
else:
    report_date = last_bday_str
    report_dt = last_bday
    comparison_date = datetime.now()

print slice_champion(report_date)