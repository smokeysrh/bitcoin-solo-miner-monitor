We are in the final stage of testing, bug finding, and bug fixing. The remaining tasks in the current tasks list focuses on expanding the functionality (none currently exists) of the Network Topology Page. This page should give the user a complete overview of their home network, this is essential to a Bitcoin miner and node operator, as the service they provide to the Bitcoin network, relies on their network remaining stable. 

When debugging, before changing or creating new code, always choose to enhance debugging first, then retest so that we accurately pin point issues before making any changes.

Always be sure to look for things that already exist so that you dont duplicate things. 

We are developing in a Windows environment, use the proper Windows commands to execute tasks:
Add files to git first with git add
Use git update-index --chmod=+x instead of chmod +x
Then set executable permissions through git
This ensures cross-platform compatibility

Always review the current infrastructure surrounding the task at hand in order to have a comprehensive overview of what already exists, this ensures we are not duplicating anything and that we are using what is already in place, in the most effective and efficient way possible.

Prior to starting a task, review the entire tasks list to understand what we've done so far and how the current task fits in to the overall big picture.

Theres an actual miner running on the network that we can use for testing 192.168.1.156. Its already been added to the app so you should see it every time.