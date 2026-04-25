- TO TEST message shortcut enable editing the prompt
- TO TEST scheduler 
- TO TEST follow-up skill - reminder should be ephemeral messages to the user
- TO TEST Generic "reply as tool" + send + Oauth
- TO TEST - bug: "confirm" as name of button is not good. If you click twice on confirm. It will send the message twice. Need to name it "Send thread reply" or "Send DM" (each tool should define at registration) and if possible, one time click, disable on send one.
- TO TEST - reply is not default, every tool print it's own confirmation. and notify only tools 
- CODING oauth
- CODING: proper tool display names, a notification of "schedule_prompt: Prompt scheduled with cron '0 9 * * *'; expires in 14 days." is weir. "schedule_prompt" is not a readable name

- built-in seed skills and installation process to copy the skills with confirmation if the skills folder is not empty
- thumb up, thumbs down => add to skill examples
- summarize skill
- urgent unread messages
- refactor data things like settings and tools saved in ~/.open_slack_copilot to database using common/data_layer/
- chat with the app itself on slack, should be free agent chat, not sure what is the difference.

Future
- chat indications
- In tool confirmation, add : powered by "open slack bot" with a link to github
- CI/CD
- ??? change M4 for watcher skills metabase.json to define who is the watcher user id. Not related to owner hcange it as wellpm
- track my follow ups, create task list for users with slack threads

CANCELLED
- seems not a real bug - suspected bug: when you have a recurring schedules, can it be that when shutting the process down for a few days, after starting it off it will run multiple tasks?
