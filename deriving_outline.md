# Outline for deriving

## Big picture
- A new session is started for each new file insertion into the database
- Each derivative type has a set of qualifiers that the file must meet to have this deriviative generated
- The qualifiers should prevent a loop of derivative generation for the derivatives themselves


## Implementation
- Each derivative kind should have a function which takes a file and session, and either qualifies it or disqualifies it for that generation
- Each derivative kind also has a function which takes the input file path of the original file, and outputs the proxy to the specified file path
- There is then a master loop which starts a new session for each file, determines if it is eligible for any proxy generation, and then generates and moves on to the next file
