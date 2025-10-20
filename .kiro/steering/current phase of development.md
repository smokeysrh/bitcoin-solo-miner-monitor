We are in the final stage of testing, bug finding, and bug fixing. The current tasks list focuses on fixing issues that may be causing the Network Scan feature to not function properly. We hope that by solving these issues that the scan function will then owork as intended.

When debugging, before changing or creating new code, always choose to enhance debugging first, then retest so that we accurately pin point issues before making any changes.

Always be sure to look for things that already exist so that you dont duplicate things.

We are developing in a Windows environment, use the proper Windows commands to execute tasks:
Add files to git first with git add
Use git update-index --chmod=+x instead of chmod +x
Then set executable permissions through git
This ensures cross-platform compatibility

Always review the current infrastructure surrounding the task at hand in order to have a comprehensive overview of what already exists, this ensures we are not duplicating anything and that we are using what is already in place, in the most effective and efficient way possible.

Review the entire tasks list (if there is one) to understand what we've done so far and how the current task fits in to the overall big picture.

Theres an actual miner running on the network that we can use for testing 192.168.1.156. Its already been added to the app so you should see it every time.