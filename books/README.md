# Numerology Books Directory

This directory contains PDF books used as context for AI report generation.

## Required File

Place your numerology reference book here with the filename:
- `numerology_book.pdf`

The book content will be automatically extracted and included in the GPT-4 context when generating reports.

## Notes

- The PDF file should contain comprehensive numerology information
- Text will be extracted automatically using PyPDF2
- The book is loaded once at application startup for performance
- Maximum recommended size: 50-100 pages to stay within token limits
