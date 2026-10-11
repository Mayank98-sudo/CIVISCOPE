"""Optional isolated-browser QA against the local development server only.

Requires Playwright in the execution environment and existing Chrome. This does
not use the user's Chrome profile or automate third-party sites.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlparse

sys.path.insert(0,str(Path(tempfile.gettempdir())/'civiscope-browser-tests'))
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8501'
if urlparse(URL).hostname not in {'127.0.0.1','localhost'}:
    raise ValueError('Browser QA is restricted to the local application')
OUT=ROOT/'docs/qa'; OUT.mkdir(exist_ok=True)
errors=[]; checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1)
    page=context.new_page()
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(URL,wait_until='domcontentloaded')
    expect(page.get_by_role('heading',name='Delhi air quality intelligence',exact=True)).to_be_visible(timeout=45000)
    expect(page.get_by_text('Understand the city. Inspect the evidence.',exact=True)).to_be_visible()
    expect(page.locator('[data-testid="stMetricValue"]').first).to_be_visible(timeout=45000)
    expect(page.locator('[data-testid="stDataFrame"]').first).to_be_visible(timeout=45000)
    page.screenshot(path=str(OUT/'overview_desktop.png'),full_page=True)
    checks.append('Desktop overview rendered')
    for name in ['Live AQI','Stations','Forecast','Trends','Risk & Warnings','Spatial Intelligence','Data Quality','Methodology','About']:
        page.get_by_text(name,exact=True).first.click()
        expect(page.get_by_role('heading',name=name,exact=True)).to_be_visible(timeout=30000)
        expect(page.locator('[data-testid="stException"]')).to_have_count(0)
        if name=='Data Quality':
            expect(page.get_by_role('heading',name='Live readiness check',exact=True)).to_be_visible(timeout=30000)
            expect(page.get_by_text('Last explicit check:',exact=False)).to_be_visible(timeout=30000)
            page.screenshot(path=str(OUT/'data_quality_desktop.png'),full_page=True)
            checks.append('Saved live readiness panel rendered with check timestamp')
        checks.append('Browser page: '+name)
    page.get_by_text('Spatial Intelligence',exact=True).first.click()
    expect(page.get_by_role('heading',name='Spatial Intelligence',exact=True)).to_be_visible()
    canvas=page.locator('canvas.maplibregl-canvas').first
    expect(canvas).to_be_visible(timeout=30000)
    box=canvas.bounding_box()
    page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
    page.mouse.wheel(0,-120)
    page.screenshot(path=str(OUT/'spatial_desktop.png'),full_page=True)
    checks.append('Map canvas rendered and zoom input accepted')
    station_picker=page.locator('[data-testid="stSelectbox"]').filter(has_text='Map station detail').get_by_role('combobox')
    expect(station_picker).to_be_visible(timeout=30000)
    station_picker.scroll_into_view_if_needed()
    station_picker.click()
    options=page.get_by_role('option')
    expect(options.nth(1)).to_be_visible()
    selected_station=options.nth(1).inner_text()
    options.nth(1).click()
    expect(page.get_by_role('heading',name=selected_station,exact=True)).to_be_visible(timeout=30000)
    checks.append('Map station selector opens station detail')
    page.get_by_text('Overview',exact=True).first.click()
    expect(page.get_by_role('heading',name='Delhi air quality intelligence',exact=True)).to_be_visible()
    mobile_context=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1)
    mobile=mobile_context.new_page()
    mobile.goto(URL,wait_until='domcontentloaded')
    expect(mobile.get_by_role('heading',name='Delhi air quality intelligence',exact=True)).to_be_visible(timeout=45000)
    expect(mobile.locator('[data-testid="stMetricValue"]').first).to_be_visible(timeout=45000)
    sidebar=mobile.locator('[data-testid="stSidebar"]')
    if sidebar.count() and sidebar.evaluate('(element) => element.getBoundingClientRect().right')>5:
        raise AssertionError('Mobile sidebar covers content on initial load')
    expect(mobile.locator('[data-testid="stException"]')).to_have_count(0)
    overflow=mobile.evaluate('document.documentElement.scrollWidth > window.innerWidth + 2')
    if overflow: raise AssertionError('Mobile document has horizontal overflow')
    mobile.screenshot(path=str(OUT/'overview_mobile.png'),full_page=True)
    checks.append('390px mobile viewport: no document horizontal overflow')
    checks.append('Mobile sidebar collapsed on initial load')
    mobile_context.close(); context.close(); browser.close()
if errors: raise AssertionError(errors)
(OUT/'browser_results.json').write_text(json.dumps({'checks':checks,'javascript_errors':errors},indent=2),encoding='utf-8')
print(json.dumps({'checks':checks,'javascript_errors':errors},indent=2))
