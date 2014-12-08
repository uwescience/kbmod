import datetime
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import seaborn as sns
import numpy as np
sns.set_style("ticks")
sns.set_context("poster")

def hacklegend():
    l1 = plt.scatter([],[], s=100*np.sqrt(1), c='r')
    l2 = plt.scatter([],[], s=100*np.sqrt(10), c='r')
    l3 = plt.scatter([],[], s=100*np.sqrt(100), c='r')
    l4 = plt.scatter([],[], s=100*np.sqrt(1000), c='r')

    labels = ["1", "10", "100", "1000"]

    leg = plt.legend([l1, l2, l3, l4], labels, ncol=4, frameon=False, fontsize="medium",
        handlelength=3, loc = 8, borderpad = 1.8, 
        handletextpad=1, title='Number Trajectories Used\n', scatterpoints = 1,
        prop = FontProperties(weight="bold"))

dates = []
times = []
sizes = []
# git blame 
dates.append(datetime.datetime(2014,10,10))
times.append(7950.380/1000)
sizes.append(1)

# git blame
dates.append(datetime.datetime(2014,10,30))
times.append(663.443/1000)
sizes.append(1)

# issue 3
dates.append(datetime.datetime(2014,11,19))
times.append(1.6)
sizes.append(1)

dates.append(datetime.datetime(2014,11,21))
times.append(1.228/5)
sizes.append(5)

dates.append(datetime.datetime(2014,11,23))
times.append(0.014)
sizes.append(100)

dates.append(datetime.datetime(2014,11,27))
times.append(34.748/5000)
sizes.append(5000)

fig, ax = plt.subplots()
ax.plot(dates, times, ls="-")
ax.scatter(dates, times, s=100*np.sqrt(sizes), c="r", zorder=1)
ax.set_ylabel("Query Time(s) per Trajectory")
hacklegend()
ax.semilogy()
ax.set_xlim(datetime.datetime(2014,9,29).toordinal(), datetime.datetime(2014, 12, 4).toordinal())
sns.despine(offset=10, trim=True)
plt.setp(ax.get_xticklabels(), rotation=20)
plt.show()