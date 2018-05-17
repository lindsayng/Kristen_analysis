import pg8000
import numpy as np
import pandas as pd
from jem_funcs import limsquery, validated_input, validated_date_input
from datetime import datetime
from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import USFederalHolidayCalendar

def get_containers(recording_date):
    """Takes a date and returns a dataframe of patched cell containers and slices from that date.
    
    Parameters
    ----------
    recording_date : string
        A date in the format YYMMDD.
    
    Returns
    -------
    Pandas dataframe
        A dataframe containing all patched cell containers and the corresponding slice names for a given day.
    """
    
    recording_date_query_str = "%%" + recording_date + "%%"
    lims_query_str="SELECT slice.name as slice, cell.patched_cell_container \
    FROM specimens cell JOIN specimens slice ON cell.parent_id = slice.id \
    JOIN projects proj ON cell.project_id = proj.id \
    WHERE proj.code <> 'mMPATCH' AND \
    cell.patched_cell_container IS NOT NULL \
    AND cell.patched_cell_container LIKE '%s'" %recording_date_query_str
    containers = pd.DataFrame(limsquery(lims_query_str))
    return containers

def get_patcher(containers, slice_name):
    """Takes a dataframe containing patched cell containers and a slice of interest
    and returns the name of the patcher who worked on that slice.
    
    Parameters
    ----------
    containers : Pandas dataframe
        A dataframe containing patched cell containers and slice names.
    slice_name : string
        The name of the slice for which the patcher is desired.
    
    Returns
    -------
    string
        The name of the patcher who worked on the slice.
    """

    users = {'P1':'Kristen', 'P2':'Rusty', 'P8':'Lindsay', 'P9':'Lisa', 'PA':'Ram', 'PB':'DiJon'}
    
    container = containers[containers['slice'] == slice_name].patched_cell_container.values[0]
    user_code = container[0:2]
    user_name = users[user_code]
    return user_name

def find_winner(containers):
    """Takes a dataframe of patched cell containers and slice names and returns the name of the
    patcher(s) with the most cells per slice.
    
    Parameters
    ----------
    containers : Pandas dataframe
        A dataframe containing patched cell containers and slice names.
    
    Returns
    -------
    string
        A message naming the patcher(s) with the most cells per slice.
    """
    
    counts = containers.groupby(['slice']).size().reset_index(name = 'cells')
    most_cells = counts['cells'].max()
    winning_slice = counts[counts['cells'] == most_cells] #all slices with maximal number of cells

    #If more than 1 winning slice, prints all winners and returns message about tie
    if len(winning_slice) > 1:
        winner_names = []
        for slice_name in winning_slice.slice:
            winner_names.append(get_patcher(containers, slice_name))
        unique_winners = np.unique(winner_names)
        num_winners = len(unique_winners)
        if num_winners == 1:
            return "%s" %unique_winners[0] + " with %d cells in a slice!" %most_cells
        else:
            for winner in unique_winners:
                print winner + " got %d cells in a slice!" %most_cells
            return "a %d way tie!" %num_winners
    #Otherwise returns single winner
    else:
        winning_slice = winning_slice.slice.values[0]
        winner = get_patcher(containers, winning_slice)
        return "%s" %winner + " with %d cells in a slice!" %most_cells


def main():
    """Prompts the user about the date for which they want the slice champion
    and prints the winner(s) for both mouse and human slices, if applicable.
    """
    
    #Get last business day
    bday_us = CustomBusinessDay(calendar=USFederalHolidayCalendar())
    last_bday = (datetime.today() - bday_us).date()
    last_bday_str = last_bday.strftime("%y%m%d")

    #Ask for user input
    str_prompt1 = "\nWould you like to report on recordings from %s? (y / n): "  %last_bday_str
    valid_vals = ["y", "n"]
    str_prompt2 = "Please enter date to report on (YYMMDD): "

    response1 = "\nPlease try again..."
    response2 = "\nPlease try again... date should be YYMMDD"

    last_bday_state = validated_input(str_prompt1, response1, valid_vals)
    if last_bday_state == "n":
        report_date = validated_date_input(str_prompt2, response2, valid_options=None)
    else:
        report_date = last_bday_str

    #Get patched cell containers
    cell_containers = get_containers(report_date)
    if cell_containers.empty:
        print "No patched cells from that date"
    else:
        #Check for human cells and print slice winners for human and mouse, if applicable
        cell_containers['human?'] = cell_containers['slice'].str.match(r"H\d\d") #creates new boolean column
        if cell_containers['human?'].any():
            human_cells = cell_containers[cell_containers['human?'] == True]
            print "The human winner is " + find_winner(human_cells)
        mouse_cells = cell_containers[cell_containers['human?'] == False]
        if not mouse_cells.empty:
            print "The mouse winner is " + find_winner(mouse_cells)

if __name__ == '__main__':
    main()