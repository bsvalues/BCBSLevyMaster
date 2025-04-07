import re

# Read the file
with open('templates/simple_base.html', 'r') as file:
    content = file.read()

# Update the CSS variables
content = re.sub(
    r'--bg-dark: #1D3A54;         /\* Slightly Lighter Navy - Background Color \*/',
    '--bg-dark: #ffffff;         /* White - For background */',
    content
)

content = re.sub(
    r'--text-light: #ffffff;      /\* Pure White - Text on dark backgrounds \*/',
    '--text-light: #333333;      /* Dark Gray - Text on light backgrounds */',
    content
)

# Update the navbar
content = re.sub(
    r'<nav class="navbar navbar-expand-lg navbar-dark bg-dark py-3">',
    '<nav class="navbar navbar-expand-lg navbar-dark py-3" style="background: linear-gradient(90deg, #2D5F8B 0%, #3DA5BD 100%);">',
    content
)

# Update the page header section
content = re.sub(
    r'<div class="bg-dark py-4">',
    '<div class="bg-light py-4">',
    content
)

# Update the footer
content = re.sub(
    r'<footer class="bg-dark text-light py-4 mt-auto" style="border-top: 4px solid var\(--primary-color\);">',
    '<footer class="bg-light text-dark py-4 mt-auto" style="border-top: 4px solid var(--primary-color);">',
    content
)

# Update any link-light to link-dark
content = re.sub(r'link-light', 'link-dark', content)

# Update any text-muted on lighter backgrounds to have more contrast
content = re.sub(r'text-muted', 'text-secondary', content)

# Write back to the file
with open('templates/simple_base.html', 'w') as file:
    file.write(content)

print("Updated simple_base.html with light theme elements")
