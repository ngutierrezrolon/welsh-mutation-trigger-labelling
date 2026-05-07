# Welsh Mutation Trigger Labelling

A web app for identifying and labelling different types of mutation triggers in Welsh. 

### Main Components:
- **CyTag** - The main component for tagging. 
The file postagger/grammar/trigger.cg was the main file introduced for the parsing, identification and tagging of mutations.
- **trigger.cg** - The Constraint Grammar (CG) rules to append trigger labels.
- **parser.py** - The helper function to parse the text through CyTag for PoS tagging and through the additional layer of CG rules for trigger labelling.
- **main.py** - The file to run the webpage front end and inject explanations for each mutation reason family, tailored to the specific trigger if relevant for additional explanations.

---

## Requirements

- Python 3
- VISL-CG3 (See CyTag's main github for additional instructions.)

---

## License 

Note that this code, like CyTag, is available under the GNU General Public License (v3).