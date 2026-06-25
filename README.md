# Filebase
### 2026-06-24

## Main entity

- **File**: An immutable sequence of bits, identified by its content hash.

## Other entities
- **Storage Devices**: Physical devices used to store files, varying in location, accessibility, capcacity, etc.

- **Technical Metadata**: Program generated values from the ones and zero sequence such as mime type, image height, video duration.

- **Derivatives**: Files that are generated from another file using a program, such as a thumbnail from a video.

- **File Instance**: A meaningful reference to a file. It records names, descriptions, tags, context, or other information about what that file means in a particular situation.

- **Bundle**: An immutable, archive-like collection of files. A bundle contains path-to-file mappings and may have its own name, description, tags, and metadata describing the bundle as a whole.

- **Directory**: A mutable filesystem-like tree used to organize file instances and bundles.

## Project philosophy
The only physical matter is magnetic orientations, electric charges, pits and valleys of the various hard drives, solid state drives, optical discs and other binary storage mediums. The main entity is the file, a specific sequence of these binary values, and that sequence is immutable. Everything else: the hashes of the files, the times they were inserted, a name given to them, what drives they are stored on, the tag entity, the bundle entity, and so on, is information used to locate, sort, filter, organize, ... these files. The primary medium to store this information is the filebase database, although the information may be stored on paper, post its, text messages, and more. This project contains the tools to create, manage, and utilize the filebase database, as well as programs to automate certain workflows.


