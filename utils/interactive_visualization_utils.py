"""
Interactive visualization utilities.

This module provides enhanced data visualization functions:
- Interactive charts with drill-down capabilities
- Map-based visualizations for geographical analysis
- Dynamic dashboards with real-time filtering
- Comparative visualizations for different scenarios
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
import numpy as np
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)


def create_interactive_chart(data: Dict[str, Any], chart_type: str = 'line') -> Dict[str, Any]:
    """
    Create a highly interactive chart configuration for Plotly.js.
    
    Args:
        data: Dictionary containing data for the chart
        chart_type: Type of chart ('line', 'bar', 'scatter', etc.)
        
    Returns:
        Dictionary with Plotly chart configuration
    """
    try:
        # Default config for all chart types
        config = {
            'displayModeBar': True,
            'responsive': True,
            'scrollZoom': True,
            'editable': True,
            'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'chart_export',
                'height': 800,
                'width': 1200,
                'scale': 2
            }
        }
        
        # Default layout settings
        layout = {
            'template': 'plotly_dark',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'margin': {
                'l': 50,
                'r': 50,
                'b': 80,
                't': 100
            },
            'hovermode': 'closest',
            'legend': {
                'orientation': 'h',
                'y': -0.2
            },
            'updatemenus': [{
                'buttons': [
                    {
                        'method': 'relayout',
                        'label': 'Reset Zoom',
                        'args': ['xaxis.range', None]
                    }
                ],
                'direction': 'left',
                'pad': {'r': 10, 't': 10},
                'showactive': False,
                'type': 'buttons',
                'x': 0.1,
                'y': 1.1,
                'xanchor': 'left',
                'yanchor': 'top'
            }]
        }
        
        # Specific chart type settings
        if chart_type == 'line':
            # Line chart specific settings
            layout.update({
                'xaxis': {
                    'showgrid': True,
                    'gridcolor': 'rgba(255,255,255,0.1)',
                    'zeroline': True,
                    'zerolinecolor': 'rgba(255,255,255,0.2)'
                },
                'yaxis': {
                    'showgrid': True,
                    'gridcolor': 'rgba(255,255,255,0.1)',
                    'zeroline': True,
                    'zerolinecolor': 'rgba(255,255,255,0.2)'
                }
            })
            
            # Adding rangeslider for easier time series exploration
            layout['xaxis']['rangeslider'] = {'visible': True}
            
        elif chart_type == 'bar':
            # Bar chart specific settings
            layout.update({
                'barmode': 'group',
                'xaxis': {
                    'showgrid': False,
                    'zeroline': False
                },
                'yaxis': {
                    'showgrid': True,
                    'gridcolor': 'rgba(255,255,255,0.1)',
                    'zeroline': True,
                    'zerolinecolor': 'rgba(255,255,255,0.2)'
                }
            })
            
        elif chart_type == 'scatter':
            # Scatter chart specific settings
            layout.update({
                'xaxis': {
                    'showgrid': True,
                    'gridcolor': 'rgba(255,255,255,0.1)',
                    'zeroline': True,
                    'zerolinecolor': 'rgba(255,255,255,0.2)'
                },
                'yaxis': {
                    'showgrid': True,
                    'gridcolor': 'rgba(255,255,255,0.1)',
                    'zeroline': True,
                    'zerolinecolor': 'rgba(255,255,255,0.2)'
                }
            })
            
            # Add zooming and selection tools
            config['modeBarButtonsToAdd'].extend(['select2d', 'lasso2d'])
            
        elif chart_type == 'heatmap':
            # Heatmap specific settings
            layout.update({
                'xaxis': {
                    'showgrid': False,
                    'zeroline': False
                },
                'yaxis': {
                    'showgrid': False,
                    'zeroline': False
                },
                'coloraxis': {
                    'colorscale': 'Viridis',
                    'colorbar': {
                        'title': {
                            'text': 'Value'
                        }
                    }
                }
            })
        
        return {
            'config': config,
            'layout': layout,
            'events': {
                'click': True,
                'hover': True,
                'selection': True,
                'zooming': True
            }
        }
    
    except Exception as e:
        logger.error(f"Error creating interactive chart: {str(e)}")
        # Return basic configuration as fallback
        return {
            'config': {
                'displayModeBar': True,
                'responsive': True
            },
            'layout': {
                'template': 'plotly_dark'
            },
            'events': {
                'click': True
            }
        }


def create_tax_district_map(district_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a map visualization for tax districts.
    
    Args:
        district_data: List of tax district data including coordinates and rates
        
    Returns:
        Map visualization configuration
    """
    try:
        # Basic map layout
        layout = {
            'mapbox': {
                'style': "dark",
                'center': {'lon': -119.44, 'lat': 46.25},  # Coordinates for Benton County, WA
                'zoom': 9
            },
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'margin': {
                'l': 10,
                'r': 10,
                'b': 10,
                't': 40
            },
            'title': 'Tax District Levy Rates',
            'coloraxis': {
                'colorscale': 'Viridis',
                'colorbar': {
                    'title': 'Levy Rate'
                }
            }
        }
        
        # Create district polygons
        data = []
        for district in district_data:
            # Extract coordinates and properties
            district_name = district.get('name', 'Unknown District')
            district_id = district.get('id', 'unknown')
            levy_rate = district.get('levy_rate', 0)
            coordinates = district.get('coordinates', [])
            
            if not coordinates:
                continue
            
            # Create polygon data
            district_polygon = {
                'type': 'choroplethmapbox',
                'z': [levy_rate],
                'locations': [district_id],
                'geojson': {
                    'type': 'FeatureCollection',
                    'features': [{
                        'type': 'Feature',
                        'properties': {
                            'id': district_id
                        },
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [coordinates]
                        }
                    }]
                },
                'featureidkey': 'properties.id',
                'coloraxis': 'coloraxis',
                'name': district_name,
                'hovertemplate': '<b>%{name}</b><br>Levy Rate: %{z:.4f}<extra></extra>'
            }
            
            data.append(district_polygon)
        
        return {
            'data': data,
            'layout': layout,
            'config': {
                'displayModeBar': True,
                'responsive': True,
                'scrollZoom': True,
                'modeBarButtonsToAdd': ['drawrect', 'eraseshape']
            }
        }
    
    except Exception as e:
        logger.error(f"Error creating tax district map: {str(e)}")
        # Return minimal data structure
        return {
            'data': [],
            'layout': {
                'title': 'Tax District Map (Error Occurred)',
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'plot_bgcolor': 'rgba(0,0,0,0)'
            },
            'config': {
                'displayModeBar': True,
                'responsive': True
            }
        }


def create_comparative_visualization(scenarios: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a visualization comparing different forecast scenarios.
    
    Args:
        scenarios: Dictionary of scenario data keyed by scenario name
        
    Returns:
        Comparative visualization configuration
    """
    try:
        data = []
        
        # Create traces for each scenario
        colors = {
            'baseline': '#3366cc',
            'optimistic': '#33cc33',
            'pessimistic': '#cc3333',
            'custom': '#cc33cc'
        }
        
        for scenario_name, scenario_data in scenarios.items():
            color = colors.get(scenario_name.lower(), '#999999')
            
            # Line trace for each scenario
            scenario_trace = {
                'x': scenario_data.get('years', []),
                'y': scenario_data.get('rates', []),
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': scenario_name.capitalize(),
                'line': {
                    'color': color,
                    'width': 2
                },
                'marker': {
                    'size': 6,
                    'color': color
                },
                'hovertemplate': f'<b>{scenario_name.capitalize()}</b><br>' +
                                 'Year: %{x}<br>' +
                                 'Rate: %{y:.4f}<extra></extra>'
            }
            
            data.append(scenario_trace)
        
        # Create layout
        layout = {
            'title': 'Scenario Comparison',
            'xaxis': {
                'title': 'Year',
                'showgrid': True,
                'gridcolor': 'rgba(255,255,255,0.1)'
            },
            'yaxis': {
                'title': 'Levy Rate',
                'tickformat': '.4f',
                'showgrid': True,
                'gridcolor': 'rgba(255,255,255,0.1)'
            },
            'legend': {
                'orientation': 'h',
                'y': -0.2
            },
            'template': 'plotly_dark',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'hovermode': 'closest',
            'margin': {
                'l': 50,
                'r': 50,
                'b': 80,
                't': 100
            },
            'updatemenus': [{
                'buttons': [
                    {
                        'method': 'update',
                        'label': 'All Scenarios',
                        'args': [{'visible': [True] * len(scenarios)}]
                    }
                ],
                'direction': 'down',
                'showactive': True,
                'x': 0.1,
                'y': 1.1,
                'xanchor': 'left',
                'yanchor': 'top'
            }]
        }
        
        # Add buttons for toggling individual scenarios
        scenario_buttons = []
        for i, scenario_name in enumerate(scenarios.keys()):
            visibility = [False] * len(scenarios)
            visibility[i] = True
            
            button = {
                'method': 'update',
                'label': scenario_name.capitalize(),
                'args': [{'visible': visibility}]
            }
            
            scenario_buttons.append(button)
        
        # Add buttons to layout
        layout['updatemenus'][0]['buttons'].extend(scenario_buttons)
        
        # Add difference visualization if there are multiple scenarios
        if len(scenarios) > 1:
            # Compute differences between each scenario and the baseline
            baseline_name = 'baseline'
            baseline_years = []
            baseline_rates = []
            
            # Find baseline scenario
            for scenario_name, scenario_data in scenarios.items():
                if scenario_name.lower() == baseline_name:
                    baseline_years = scenario_data.get('years', [])
                    baseline_rates = scenario_data.get('rates', [])
                    break
            
            # If no explicit baseline, use the first scenario
            if not baseline_rates and scenarios:
                first_scenario = list(scenarios.values())[0]
                baseline_years = first_scenario.get('years', [])
                baseline_rates = first_scenario.get('rates', [])
                baseline_name = list(scenarios.keys())[0]
            
            # Create difference traces
            for scenario_name, scenario_data in scenarios.items():
                if scenario_name.lower() == baseline_name.lower():
                    continue
                
                scenario_years = scenario_data.get('years', [])
                scenario_rates = scenario_data.get('rates', [])
                
                # Ensure years match for comparison
                if baseline_years != scenario_years:
                    continue
                
                # Calculate differences
                diff_rates = [
                    scenario_rates[i] - baseline_rates[i]
                    for i in range(len(baseline_rates))
                ]
                
                # Create difference trace
                diff_trace = {
                    'x': scenario_years,
                    'y': diff_rates,
                    'type': 'bar',
                    'name': f'{scenario_name.capitalize()} vs {baseline_name.capitalize()}',
                    'marker': {
                        'color': colors.get(scenario_name.lower(), '#999999'),
                        'opacity': 0.6
                    },
                    'hovertemplate': f'<b>{scenario_name.capitalize()} vs {baseline_name.capitalize()}</b><br>' +
                                     'Year: %{x}<br>' +
                                     'Difference: %{y:.4f}<extra></extra>',
                    'visible': 'legendonly'  # Hidden by default
                }
                
                data.append(diff_trace)
        
        return {
            'data': data,
            'layout': layout,
            'config': {
                'displayModeBar': True,
                'responsive': True,
                'scrollZoom': True
            }
        }
    
    except Exception as e:
        logger.error(f"Error creating comparative visualization: {str(e)}")
        return {
            'data': [],
            'layout': {
                'title': 'Scenario Comparison (Error Occurred)',
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'plot_bgcolor': 'rgba(0,0,0,0)'
            },
            'config': {
                'displayModeBar': True,
                'responsive': True
            }
        }


def create_dynamic_dashboard(datasets: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a dynamic dashboard with multiple visualizations and filtering options.
    
    Args:
        datasets: Dictionary containing multiple datasets for visualizations
        
    Returns:
        Dashboard configuration
    """
    try:
        dashboard = {
            'panels': [],
            'filters': [],
            'interactions': {}
        }
        
        # Create filters based on available data
        available_filters = []
        
        if 'years' in datasets:
            years = datasets['years']
            available_filters.append({
                'id': 'year_filter',
                'type': 'range',
                'label': 'Year Range',
                'min': min(years) if years else 2015,
                'max': max(years) if years else 2025,
                'values': [min(years) if years else 2015, max(years) if years else 2025],
                'step': 1
            })
        
        if 'districts' in datasets:
            districts = datasets['districts']
            available_filters.append({
                'id': 'district_filter',
                'type': 'multiselect',
                'label': 'Tax Districts',
                'options': [
                    {'value': district['id'], 'label': district['name']}
                    for district in districts
                ],
                'values': [district['id'] for district in districts][:5]  # Default to first 5
            })
        
        if 'scenarios' in datasets:
            scenarios = datasets['scenarios']
            available_filters.append({
                'id': 'scenario_filter',
                'type': 'multiselect',
                'label': 'Scenarios',
                'options': [
                    {'value': scenario, 'label': scenario.capitalize()}
                    for scenario in scenarios
                ],
                'values': list(scenarios)
            })
        
        dashboard['filters'] = available_filters
        
        # Create panels based on available data
        panels = []
        
        # Main time series panel
        if 'historical' in datasets and ('forecasts' in datasets or 'scenarios' in datasets):
            time_series_panel = {
                'id': 'time_series_panel',
                'title': 'Levy Rate Trends',
                'type': 'time_series',
                'data_source': 'time_series_data',
                'layout': {
                    'x': 0,
                    'y': 0,
                    'w': 12,
                    'h': 6
                },
                'config': create_interactive_chart({}, 'line')
            }
            panels.append(time_series_panel)
        
        # District map panel
        if 'districts' in datasets and all('coordinates' in district for district in datasets['districts']):
            map_panel = {
                'id': 'district_map_panel',
                'title': 'Tax District Map',
                'type': 'map',
                'data_source': 'district_map_data',
                'layout': {
                    'x': 0,
                    'y': 6,
                    'w': 6,
                    'h': 6
                },
                'config': create_tax_district_map(datasets['districts'])
            }
            panels.append(map_panel)
        
        # Statistics panel
        if 'statistics' in datasets:
            stats_panel = {
                'id': 'statistics_panel',
                'title': 'Summary Statistics',
                'type': 'stats',
                'data_source': 'statistics_data',
                'layout': {
                    'x': 6,
                    'y': 6,
                    'w': 6,
                    'h': 3
                }
            }
            panels.append(stats_panel)
        
        # Recommendations panel
        if 'recommendations' in datasets:
            recommendations_panel = {
                'id': 'recommendations_panel',
                'title': 'AI Recommendations',
                'type': 'recommendations',
                'data_source': 'recommendations_data',
                'layout': {
                    'x': 6,
                    'y': 9,
                    'w': 6,
                    'h': 3
                }
            }
            panels.append(recommendations_panel)
        
        dashboard['panels'] = panels
        
        # Define interactions between panels and filters
        interactions = {}
        
        for panel in panels:
            panel_id = panel['id']
            interactions[panel_id] = {
                'responds_to': [filter_config['id'] for filter_config in available_filters],
                'triggers': []
            }
        
        # Add interactions between panels
        if 'district_map_panel' in [panel['id'] for panel in panels]:
            for panel in panels:
                if panel['id'] != 'district_map_panel':
                    interactions[panel['id']]['responds_to'].append('district_map_panel')
            
            interactions['district_map_panel']['triggers'] = [
                panel['id'] for panel in panels if panel['id'] != 'district_map_panel'
            ]
        
        dashboard['interactions'] = interactions
        
        return dashboard
    
    except Exception as e:
        logger.error(f"Error creating dynamic dashboard: {str(e)}")
        return {
            'panels': [],
            'filters': [],
            'interactions': {}
        }