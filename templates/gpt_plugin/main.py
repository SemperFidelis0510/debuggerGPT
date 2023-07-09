import quart
from quart import request, Response
import json

app = quart.Quart(__name__)

@app.route('/process', methods=['POST'])
async def process():
    data = await request.get_json()
    input_data = data.get('input', '')
    output_data = input_data.upper()
    return Response(json.dumps({'output': output_data}), mimetype='application/json')

def main():
    app.run(debug=True, host="0.0.0.0", port=5003)

if __name__ == "__main__":
    main()
