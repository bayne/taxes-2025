* title26.md is the full legal text describing the US tax code
* NOTES.md was a file derived from title26.md focusing on relevant information from title26.md for individual income taxes
* SUMMARY.md was derived from title26.md that went section by section summarizing each of them and including a paragraph that indicates its relevance to filing a personal income tax return

## Overall goal
The overall goal of this project is to create a CLI tool that accepts a JSON with tax filer information and outputs JSON that can be directly applied to a tax return form. The intent is to create a data model for personal income tax returns, validate the input data, calculate necessary fields, validate the calculated fields and have a system accept information about an individual to be able to fill out all the relevant forms expected for the federal tax return

TASKS:
1. Use SUMMARY.md to review NOTES.md for correctness and make updates to NOTES.md to add knowledge about personal tax returns. Follow references that point to title26.md in each of the files to gather more information if needed for the topic
2. Commit the NOTES.md file once complete
3. Create a data model in python using multiple @dataclass to capture all relevant information necessary to be able to file a tax return. Document each dataclass and include references to the specific sections in the tax code. The data model must be describeable as a json-schema.
4. Write a python script for the rest of validations, constraints, and calculations that cannot be expressed through json-schema. The python script will accept and instance of data model as described by the json-schema. The script will output a new datamodel with all the final forms of the data that can eventually be submitted as a tax return. The new datamodel must be describeable as a json-schema. Make sure to document the calculated fields with references to their sources

## Additional details
Make reasonable assumptions and use JSON as the primary data format.
