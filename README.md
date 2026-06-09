# Filebase
### 2026-06-09

## Main entity:
- **File**:A specific sequence of bits which is never modified

## Ideas for other information stored in filebase:
- **Storage device**: An entity which corresponds to a physical storage medium. We record its physical location, capacity, what files are on it, etc.
- **Bundle**:An entity which contains a set of files and / or bundles which is never modified
- **Tag**: An entity which contains a set of files which can always change
- **File description**: A user written semantic description of the meaning of the file, used for semantic search and more

## Project philosophy
The only physical matter is magnetic orientations, electric charges, pits and valleys of the various hard drives, solid state drives, optical discs and other binary storage mediums. The main entity is the file, a specific sequence of these binary values, and that sequence is immutable. Everything else: the hashes of the files, the times they were inserted, a name given to them, what drives they are stored on, the tag entity, the bundle entity, and so on, is information used to locate, sort, filter, organize, ... these files. The primary medium to store this information is the filebase database, although the information may be stored on paper, post its, text messages, and more. This project contains the tools to create, manage, and utilize the filebase database, as well as programs to automate certain workflows.


