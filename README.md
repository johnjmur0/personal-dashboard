
# personal-dashboard
Currently a work in progress, but it's a plotly/dash dashboard to display disparate data sources I utilize. 

Sources include:
- 
  - Personal finances with Mint: https://mint.intuit.com/
    - More specifically, I actually have another repo in R/python: https://github.com/johnjmur0/financial-management
      - This repo relies on this other awesome project to scrape data from Mint b/c they don't have a real API: https://github.com/mintapi/mintapi
     - I then use my other repo to process that raw Mint data, and expose it as an API so from the dashboard's perspective it's the same as all the these other  services.  
  - Tasks, schedules, tracking and overall producitivity with Marvin: https://amazingmarvin.com/
    - I really love Marvin. Couldn't recommend it enough :)
  - More tracking with Exist: https://exist.io/
    - As I continue using Marvin, I may end up dropping Exist and using Marvin instead.

Right now it's pretty basic, but I plan on continuing to build it up to help with my budgeting and financial planning, and other goals like health and fitness. 

Other objectives were to:
-
- Have some public python code :)
- Get some experience with Dash
	- Which to be honest I didn't love - figuring out the dbc layouts and all the optional parameters felt like a cruel puzzle, and actually getting it to look good felt like too much googling for too little improvement. Suffice to say I will be happy to not be the best UI person on a team. 
  
  
Since its totally custom to me and connected to these data sources (some of which are subscriptions), please don't try to fork it without letting me know. I'd be happy to help you get something working on your end, but have no interest in maintaining this for anyone other than myself. 

But if you're a Mint, Marvin, Exist user, feel to reach out or checkout how I've processed those. Each were unique in their own way. :)

P.S. I wiped the commit history b/c when I was prototying I had some config info hardcoded.

Here's an example of how it looks now (with some actual data 0'd out): 
![image](https://user-images.githubusercontent.com/87945603/196010565-07a6f315-2d67-449b-a1c5-fd4f61aad8e6.png)
