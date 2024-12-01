// Import the functions you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.7/firebase-app.js";
import { getMessaging, getToken, onMessage } from "https://www.gstatic.com/firebasejs/9.6.7/firebase-messaging.js";

// Firebase configuration
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

// Request permission to receive notifications
export function requestNotificationPermission() {
  Notification.requestPermission()
    .then((permission) => {
      if (permission === "granted") {
        console.log("Notification permission granted.");
        getDeviceToken();
      } else {
        console.log("Notification permission not granted.");
      }
    })
    .catch((err) => {
      console.error("Error requesting notification permission:", err);
    });
}

// Get device token
export function getDeviceToken() {
  getToken(messaging, { vapidKey: "YOUR_VAPID_KEY" })
    .then((currentToken) => {
      if (currentToken) {
        console.log("Device token:", currentToken);
        // Send this token to your server
        sendTokenToServer(currentToken);
      } else {
        console.log("No registration token available. Request permission to generate one.");
      }
    })
    .catch((err) => {
      console.error("Error retrieving token:", err);
    });
}

// Send device token to the server
function sendTokenToServer(token) {
  fetch("/save-device-token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token }),
  }).then((response) => {
    if (response.ok) {
      console.log("Token saved successfully.");
    } else {
      console.error("Error saving token:", response.statusText);
    }
  });
}

// Handle foreground messages
onMessage(messaging, (payload) => {
  console.log("Message received. ", payload);
});
