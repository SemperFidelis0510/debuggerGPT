import pandas as pd
import matplotlib.pyplot as plt
from pandas.plotting import table

# Create a DataFrame from the provided data
schedule = [
    ['August 7', 'Monday', '12:00 - 12:45', '1 - Inequalities'],
    ['August 7', 'Monday', '13:45 - 14:30', '2 - Induction, Bernoulli, Averages'],
    ['August 8', 'Tuesday', '12:00 - 12:45', '3 - Bounded Sets'],
    ['August 8', 'Tuesday', '13:45 - 14:30', '4 - UpperLowerBounds'],
    ['August 9', 'Wednesday', '12:00 - 12:45', '5 - Convergence'],
    ['August 9', 'Wednesday', '13:45 - 14:30', '6 - ArithmeticsSandwich'],
    ['August 10', 'Thursday', '12:00 - 12:45', '7 - Infinite Limit'],
    ['August 10', 'Thursday', '13:45 - 14:30', '8 - Root and Ratio Test'],
    ['August 11', 'Friday', '12:00 - 12:45', '9 - CantorSubseries'],
    ['August 13', 'Sunday', '12:00 - 12:45', '10 - Subseries'],
    ['August 13', 'Sunday', '13:45 - 14:30', '11 - LimsupLiminf'],
    ['August 14', 'Monday', '12:00 - 12:45', '12 - CauchyBorel'],
    ['August 14', 'Monday', '13:45 - 14:30', '13 - RealPowers'],
    ['August 15', 'Tuesday', '12:00 - 12:45', '14 - Function'],
    ['August 15', 'Tuesday', '13:45 - 14:30', '15 - PointLimit'],
    ['August 16', 'Wednesday', '12:00 - 12:45', '16 - PointArithmetic'],
    ['August 16', 'Wednesday', '13:45 - 14:30', '17 - OneSideBroadCauchy'],
    ['August 17', 'Thursday', '12:00 - 12:45', '18 - Continuity'],
    ['August 17', 'Thursday', '13:45 - 14:30', '19 - Weirstrass'],
    ['August 18', 'Friday', '12:00 - 12:45', '20 - UniformContandDerivatives'],
    ['August 20', 'Sunday', '12:00 - 12:45', '21 - ChainRuleInverse'],
    ['August 20', 'Sunday', '13:45 - 14:30', '22 - ExremumFermatRolle'],
    ['August 21', 'Monday', '12:00 - 12:45', '23 - DarbouxBoudDerivatives'],
    ['August 21', 'Monday', '13:45 - 14:30', '24 - L'HopitalTaylor'],
    ['August 22', 'Tuesday', '12:00 - 12:45', '25 - Littleo']
]
df = pd.DataFrame(schedule, columns=['Date', 'Day of Week', 'Time', 'Topic'])

# Create a figure and a single subplot
fig, ax = plt.subplots(figsize=(12, 4))

# Hide axes
ax.xaxis.set_visible(False) 
ax.yaxis.set_visible(False) 

# Table from DataFrame
tab = table(ax, df, loc='center', cellLoc = 'center')

# Autoresize the columns
plt.gcf().tight_layout()

# Save the figure as a PDF
plt.savefig('P:\Scripts\debuggerGPT\capabilities\schedule.pdf')
