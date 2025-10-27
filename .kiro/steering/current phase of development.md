We are reworking the Installer. Review the requirments, design, and tasks list for this spec, installer-simplification-refactor for context.

When debugging, before changing or creating new code, always choose to enhance debugging first, then retest so that we accurately pinpoint issues before making any changes.

Always be sure to look for things that already exist so that you dont duplicate things. 

We are developing in a Windows environment, use the proper Windows commands to execute tasks:
Add files to git first with git add
Use git update-index --chmod=+x instead of chmod +x
Then set executable permissions through git
This ensures cross-platform compatibility

Prior to starting a task, review the entire tasks list to understand what we've done so far and how the current task fits in to the overall big picture.

Theres an actual miner running on the network that we can use for testing 192.168.1.156. Its already been added to the app so you should see it every time.