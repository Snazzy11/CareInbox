import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

import { MantineProvider } from '@mantine/core';
import { Router } from './Router';
import { theme } from './theme';
import { Notifications } from "@mantine/notifications";

export default function App() {
  return (
    <MantineProvider theme={theme}>
        <Notifications position="top-right" limit={1}/>
        <Router />
    </MantineProvider>
  );
}
