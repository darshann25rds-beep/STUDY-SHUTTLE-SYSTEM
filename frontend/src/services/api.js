import axios from "axios";

const API = axios.create({
    baseURL: "http://127.0.0.1:8000",
});

API.interceptors.request.use((config) => {
    try {
        const signedIn = JSON.parse(sessionStorage.getItem("studyShuttleUser") || "null");
        if (signedIn?.token) config.headers.Authorization = `Bearer ${signedIn.token}`;
    } catch {
        sessionStorage.removeItem("studyShuttleUser");
    }
    return config;
});

export default API;
