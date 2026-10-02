import datetime


# date_in format: yyyy-mm-ddTHH:MM:SS
def iso_datestring_to_date(date_in):
    try:
        return datetime.datetime.strptime(date_in.split("T")[0], '%Y-%m-%d').date()
    except (AttributeError, TypeError, ValueError):
        return None
