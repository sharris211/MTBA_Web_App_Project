from flask import Flask, render_template, request
from MBTAHelper import find_stop_near

app = Flask(__name__)

@app.route('/')
def index():
    """Display search form"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Handle search request"""
    try:
        place_name = request.form.get('place_name')
        if not place_name:
            return render_template('index.html', error="Please enter a location")
        
        result = find_stop_near(place_name)
        if 'error' in result:
            return render_template('index.html', error=result['error'])
            
        return render_template('result.html', **result)
        
    except Exception as e:
        print(f"Error in search route: {str(e)}")  # Debug print
        return render_template('index.html', error=f"An error occurred: {str(e)}")


print("Starting Flask app...")
app.run(debug=True)