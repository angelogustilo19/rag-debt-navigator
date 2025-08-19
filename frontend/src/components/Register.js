import React, { useState } from 'react';
import axios from 'axios';
import { TextField, Button, Typography, Box, Paper } from '@mui/material';

function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://127.0.0.1:8000/register', { username, password });
      setMessage(response.data.message);
    } catch (error) {
      if (error.response) {
        setMessage(error.response.data.detail);
      } else {
        setMessage('Network Error or Server Unreachable');
      }
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 4, mt: 4, bgcolor: 'white' }}>
      <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
        <Typography component="h1" variant="h5" align="center" sx={{ color: '#1B5E20' }}>
          Register
        </Typography>
        <TextField
          margin="normal"
          required
          fullWidth
          id="username"
          label="Username"
          name="username"
          autoComplete="username"
          autoFocus
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <TextField
          margin="normal"
          required
          fullWidth
          name="password"
          label="Password"
          type="password"
          id="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button
          type="submit"
          fullWidth
          variant="contained"
          sx={{ mt: 3, mb: 2, bgcolor: '#1B5E20', '&:hover': { bgcolor: '#2E7D32' } }}
        >
          Register
        </Button>
        {message && <Typography color="success.main" align="center">{message}</Typography>}
      </Box>
    </Paper>
  );
}

export default Register;
