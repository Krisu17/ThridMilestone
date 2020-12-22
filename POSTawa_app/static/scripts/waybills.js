const DELETE = "DELETE";
const GET = "GET";
const URL_TO_DB = "https://localhost:8080/waybill/";
const URL_TO_FILE = "https://localhost:8081/waybill/";
var HTTP_STATUS = {OK: 200, BAD_REQUEST: 400, UNAUTHORIZED: 401, FORBIDDEN: 403, NOT_FOUND: 404};
    
    
    
async function removeWaybill(hash_name) {
    
    let removeFileURL = URL_TO_FILE + "rm/" + hash_name;
    let removeFromDbURL = URL_TO_DB + "rm/" + hash_name;
    let rmParams = {
        method: DELETE,
        redirect: "follow"
    }
    let res = await fetch (removeFileURL, rmParams);
    if (res.status === HTTP_STATUS.OK) {
        console.log("Status file: " + res.status)
        let res2 = await fetch (removeFromDbURL, rmParams);
        if (res2.status === HTTP_STATUS.OK) {
            console.log("Poprawnie usunięto.")
            document.getElementById(hash_name).innerHTML = ""
        } else if(res2.status === HTTP_STATUS.FORBIDDEN) {
            alert("Nie można usunąć listu przewozowego.\nPaczka została już nadana.")
        } else {
            alert("Wystąpił błąd podczas usuwania. \nSpróbuj zalogować się ponownie i spróbuj jeszcze raz.")
        }
    } else if (res.status == HTTP_STATUS.FORBIDDEN) {

        alert("Nie można usunąć listu przewozowego.\nPaczka została już nadana.")
    } else {
        console.log("Unknown error: " +res.status)
    }
}



