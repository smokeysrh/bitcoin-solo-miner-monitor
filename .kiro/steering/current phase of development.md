We are in the final stage of testing, bug finding, and bug fixing. do not add any additional features outside of what is required by the task at hand. We do not want to introduce new bugs while fixing current bugs. When debugging, before changing or creating new code, always choose to enhance debugging first, then retest so that we accurately pin point issues before making changes.

We have identified multiple issues with the Installer and are now in the middle of making the changes with the professional-installer-distribution Spec. Remember that we have much installer code wrote, we should build from or build upon this foundation to complete the tasks.md.

We are developing in a Windows environment, use the proper Windows commands to execute tasks:
Use git update-index --chmod=+x instead of chmod +x
Add files to git first with git add
Then set executable permissions through git
This ensures cross-platform compatibility

Always review the current infrastructure surrounding the task at hand in order to have a comprehensive overview of what already exists, this ensures we are not duplicating anything and that we are using what is already in place, in the most effective and efficient way possible.

