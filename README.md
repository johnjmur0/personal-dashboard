# personal-dashboard
Currently a work in progress, but it's a plotly/dash dashboard to display disparate data sources I utilize. 

Sources include:
  - Personal finances with Mint: https://mint.intuit.com/
    - More specifically, I actually have another repo in R/python: https://github.com/johnjmur0/financial-management
      that relies on this other awesome project to scrape data from Mint b/c they don't have a real API: https://github.com/mintapi/mintapi
      I then use my other repo to process that raw Mint data, and expose it as an API so from the dashboard's perspective it's the same as all the these other  -         services.  
  - Tasks, schedules, tracking and overall producitivity with Marvin: https://amazingmarvin.com/
    - I really love Marvin. Couldn't recommend it enough :)
  - More tracking with Exist: https://exist.io/
    - As I continue using Marvin, I may end up dropping Exist and using Marvin instead.

Right now it's pretty basic, but I plan on continuing to build it up to help with my budgeting and financial planning, and other goals like health and fitness. 
Other objectives were to:
  1. Get some experience with Dash
    - Which to be honest I didn't love - figuring out the dbc component order and all the optional parameters felt like a cruel puzzle,
      and the "artistry" elements feels like wasted time but I also hated how ugly it looked
  2. Have some public python code :)
  
Since its totally custom to me and connected to these data sources (some of which are subscriptions), it's not available for public use at this time. 
But if you're a Mint, Marvin, Exist user, feel to reach out or checkout how I've processed those. Each were unique in their own way. :)
P.S. I wiped the commit history b/c when I was prototying I had some config info hardcoded.

Here's an example of how it looks now (with some actual data 0'd out): 
![image](https://user-images.githubusercontent.com/87945603/196010565-07a6f315-2d67-449b-a1c5-fd4f61aad8e6.png)
