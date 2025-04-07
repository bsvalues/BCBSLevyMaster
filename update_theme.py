with open('templates/base.html', 'r') as file:
    content = file.read()

# Update body styles to ensure light theme
if 'data-bs-theme="light"' in content:
    print("Light theme is already set in HTML tag")
else:
    # Make sure it's light
    content = content.replace('data-bs-theme="dark"', 'data-bs-theme="light"')
    print("Updated HTML tag to light theme")

# Find the styles section and update colors
style_start = content.find("<style>")
style_end = content.find("</style>", style_start)

if style_start != -1 and style_end != -1:
    # Original styles section
    original_styles = content[style_start + len("<style>"):style_end]
    
    # Updated styles with lighter colors
    updated_styles = """
        /* Benton County Light Modern Color Scheme */
        :root {
            --primary-color: #3DA5BD;   /* Lighter Teal Blue - Primary Brand Color */
            --secondary-color: #66A355; /* Lighter Green - Secondary Brand Color */
            --accent-color: #7CBFCC;    /* Light Teal - Accent Color */
            --bg-dark: #ffffff;         /* White - For dark backgrounds that need to be lightened */
            --bg-light: #f8fafc;        /* Very Light Gray - Light Background */
            --text-light: #333333;      /* Dark Gray - Text on light backgrounds */
            --text-dark: #333333;       /* Dark Slate - Text on light backgrounds */
            --benton-yellow: #F0C75C;   /* Brighter Yellow accent */
            --border-color: #e5e7eb;    /* Light Border Color */
            --card-bg: #ffffff;         /* Card Background */
            --hover-bg: #f1f5f9;        /* Hover Background */
        }
        
        /* Base Elements */
        body {
            color: var(--text-dark);
            background-color: var(--bg-light);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            letter-spacing: -0.011em;
        }
        
        /* Navbar Styling */
        .navbar {
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            background: linear-gradient(90deg, #2D5F8B 0%, #3DA5BD 100%) !important;
            border-bottom: none;
            padding: 0.75rem 0;
        }
        
        .navbar-dark .navbar-nav .nav-link {
            color: rgba(255, 255, 255, 0.9);
            font-weight: 500;
            padding: 0.75rem 1rem;
            transition: all 0.2s ease;
        }
        
        .navbar-dark .navbar-nav .nav-link:hover {
            color: #ffffff;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 0.25rem;
        }
        
        .navbar-dark .navbar-nav .nav-link.active {
            background-color: rgba(255, 255, 255, 0.2) !important;
            border-radius: 0.25rem;
            font-weight: 600;
        }
        
        .navbar-brand {
            font-weight: 600;
            letter-spacing: -0.02em;
        }
        
        /* Buttons */
        .btn {
            font-weight: 500;
            padding: 0.5rem 1.25rem;
            border-radius: 0.375rem;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        
        .btn-primary {
            background-color: var(--primary-color) !important;
            border-color: var(--primary-color) !important;
        }
        
        .btn-primary:hover, .btn-primary:focus {
            background-color: #2994ac !important;
            border-color: #2994ac !important;
            box-shadow: 0 4px 6px rgba(29, 78, 216, 0.1), 0 2px 4px rgba(0, 0, 0, 0.1);
            transform: translateY(-1px);
        }
        
        /* Cards */
        .card {
            border-radius: 0.5rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02), 0 1px 3px rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease;
            background-color: var(--card-bg);
        }
        
        .card:hover {
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.04), 0 4px 6px rgba(0, 0, 0, 0.05);
            transform: translateY(-2px);
        }
        
        .card-header {
            border-bottom: 1px solid var(--border-color);
            background-color: rgba(248, 250, 252, 0.8);
            font-weight: 600;
        }
        
        /* Custom header with Benton County vineyard image */
        .app-header-bg {
            background-image: linear-gradient(90deg, rgba(29, 58, 84, 0.75), rgba(61, 165, 189, 0.75)), 
                             url('{{ url_for('static', filename='images/benton-county-header.png') }}');
            background-size: cover;
            background-position: center;
            color: white;
            padding: 2rem 0;
            margin-bottom: 2rem;
            border-bottom: none;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        .app-header-bg h1 {
            font-weight: 700;
            letter-spacing: -0.03em;
        }
        
        .app-header-bg .lead {
            font-weight: 400;
            opacity: 0.9;
        }
        
        /* Text colors */
        .text-primary {
            color: var(--primary-color) !important;
        }

        /* Override any dark mode styles */
        .bg-dark {
            background-color: #ffffff !important;
            color: #333333 !important;
        }

        .text-light {
            color: #333333 !important;
        }

        /* Tables */
        .table {
            color: var(--text-dark);
        }

        /* Help menu styling - lighter version */
        .help-menu {
            background-color: white;
            color: var(--text-dark);
            border-left: 1px solid var(--border-color);
        }
    """
    
    # Replace styles
    content = content[:style_start + len("<style>")] + updated_styles + content[style_end:]
    print("Updated styles section with lighter colors")

# Remove existing light-theme.css if it exists
css_line = '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/light-theme.css\') }}">'
if css_line in content:
    content = content.replace(css_line, '')
    print("Removed light-theme.css link (now using inline styles)")

# Write the updated content back to the file
with open('templates/base.html', 'w') as file:
    file.write(content)
    print("Updated base.html successfully")
