with open('templates/base.html', 'r') as file:
    content = file.read()

# Find the position after the loading-animations.css line
search_line = '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/animations/loading-animations.css\') }}">'
light_theme_line = '    <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/light-theme.css\') }}">'

if search_line in content:
    # Insert after the loading-animations line
    modified_content = content.replace(search_line, search_line + '\n' + light_theme_line)
    
    with open('templates/base.html', 'w') as file:
        file.write(modified_content)
    print("Light theme CSS added successfully")
else:
    print("Search line not found")
