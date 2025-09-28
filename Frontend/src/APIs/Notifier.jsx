import React, { useEffect } from "react";
import { notifications } from "@mantine/notifications";
import axios from "axios";

function Notifier() {
    useEffect(() => {

        let config = {
            headers: {
                "ngrok-skip-browser-warning": "69420"
            }
        }

        const interval = setInterval(async () => {
            try {

                // const response = await axios.get("http://localhost:8000/notifications");
                const response = await axios.get(
                    "https://nonperjured-shakeable-aurore.ngrok-free.dev/emergency/status",
                    config
                );
                // TODO: Send post to false once handled

                console.log(response.data);

                if (response?.data?.emergency_active) {
                    notifications.show({
                        color: "red",
                        title: "Patient Emergency",
                        message: "The agent has detected a patient emergency. Please manually intervene.",
                        autoClose: false
                    });
                }
            } catch (err) {
                console.error("Error fetching notifications", err);
            }
        }, 7000);

        return () => clearInterval(interval); // Cleanup on unmount
    }, []);

    return null;
}

export default Notifier;
