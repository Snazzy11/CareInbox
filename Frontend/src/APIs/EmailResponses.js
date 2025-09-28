

import axios from "axios";

axios({
    method: 'get',
    url: 'http://localhost:8000/',
    responseType: 'stream'
})
    .then(function (response) {
        // response.data.pipe(fs.createWriteStream('ada_lovelace.jpg'))
        return response.data;
    });

export async function fetchRoot() {
    const response = await axios.get("http://localhost:8000/")
    return response.data
}