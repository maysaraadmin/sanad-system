# Arabic date and time formats

# Date formats
DATE_FORMAT = 'Y/m/d'             # 2023/10/15
TIME_FORMAT = 'H:i'               # 14:30
DATETIME_FORMAT = 'Y/m/d H:i'     # 2023/10/15 14:30
YEAR_MONTH_FORMAT = 'F Y'         # October 2023
MONTH_DAY_FORMAT = 'F j'          # October 15
SHORT_DATE_FORMAT = 'Y/m/d'       # 2023/10/15
SHORT_DATETIME_FORMAT = 'Y/m/d H:i'  # 2023/10/15 14:30

# First day of week (0=Sunday, 1=Monday, 6=Saturday)
FIRST_DAY_OF_WEEK = 6  # Saturday

# Date input formats
DATE_INPUT_FORMATS = [
    '%Y/%m/%d',  # '2023/10/15'
    '%d/%m/%Y',  # '15/10/2023'
    '%Y-%m-%d',  # '2023-10-15'
]

# Time input formats
TIME_INPUT_FORMATS = [
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',        # '14:30'
]

# Datetime input formats
DATETIME_INPUT_FORMATS = [
    '%Y/%m/%d %H:%M:%S',     # '2023/10/15 14:30:59'
    '%Y/%m/%d %H:%M',        # '2023/10/15 14:30'
    '%Y-%m-%d %H:%M:%S',     # '2023-10-15 14:30:59'
    '%Y-%m-%d %H:%M',        # '2023-10-15 14:30'
    '%d/%m/%Y %H:%M:%S',     # '15/10/2023 14:30:59'
    '%d/%m/%Y %H:%M',        # '15/10/2023 14:30'
]
