import datetime


# date_in format: yyyy-mm-ddTHH:MM:SS
def iso_datestring_to_date(date_in):
    try:
        try:
            date_in = date_in.split("T")[0]
        except:
            pass
        finally:
            date_out = datetime.datetime.strptime(date_in, '%Y-%m-%d')
            return date_out.date()
    except:
        return None
