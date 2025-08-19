import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, AppBar, Toolbar, Typography, Button, Container } from '@mui/material';
import Login from './components/Login';
import Register from './components/Register';
import Chatbot from './components/Chatbot';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1B5E20', // dark green
    },
    secondary: {
      main: '#FFFFFF', // white
    },
  },
});

function App() {
  const [userId, setUserId] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const storedUserId = localStorage.getItem('user_id');
    if (storedUserId) {
      setUserId(parseInt(storedUserId));
      setIsLoggedIn(true);
    }
  }, []);

  const handleLoginSuccess = (id) => {
    setUserId(id);
    setIsLoggedIn(true);
    localStorage.setItem('user_id', id);
    setMessage('');
  };

  const handleLogout = () => {
    setUserId(null);
    setIsLoggedIn(false);
    localStorage.removeItem('user_id');
    setMessage('Logged out successfully.');
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar position="static" sx={{ bgcolor: '#1B5E20' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, color: 'white', fontWeight: 'bold' }}>
            Momentum AI
          </Typography>
          {isLoggedIn && <Button color="inherit" onClick={handleLogout}>Logout</Button>}
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        {message && <Typography color="error">{message}</Typography>}
        {isLoggedIn ? (
          <Chatbot />
        ) : (
          <>
            <Login onLoginSuccess={handleLoginSuccess} />
            <Register />
          </>
        )}
      </Container>
    </ThemeProvider>
  );
}

export default App;
