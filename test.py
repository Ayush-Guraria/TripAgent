
from Tools.tavily_tool import tavily_search
from Tools.flight_tool import search_flights

# res = tavily_search("Top Rated Budget Hotels in Pittsburgh")
# print(res)

res = search_flights("Plan a 7 days Japan trip from India")
print(res)