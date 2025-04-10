import React, { useState, useEffect } from 'react';
import { 
  Container, Typography, Paper, Table, TableBody, TableCell, 
  TableContainer, TableHead, TableRow, TablePagination, 
  TextField, MenuItem, Select, FormControl, InputLabel, 
  Button, Grid, FormControlLabel, Switch, CircularProgress,
  Alert, Box
} from '@mui/material';
import axios from 'axios';
import { saveAs } from 'file-saver';

function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 10000,
});

const columns = [
  { id: 'employee_id', label: 'ID', sortable: true },
  { id: 'first_name', label: 'Имя', sortable: true },
  { id: 'last_name', label: 'Фамилия', sortable: true },
  { id: 'email', label: 'Email', sortable: true },
  { id: 'salary', label: 'Зарплата', sortable: true },
  { id: 'hire_date', label: 'Дата найма', sortable: true },
  { id: 'is_manager', label: 'Менеджер', sortable: true },
  { id: 'performance_rating', label: 'Рейтинг', sortable: true },
  { id: 'department', label: 'Отдел', sortable: true },
  { id: 'department_budget', label: 'Бюджет отдела', sortable: true },
  { id: 'projects_count', label: 'Проекты', sortable: true }
];

function App() {
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalEmployees, setTotalEmployees] = useState(0);
  
  const [filters, setFilters] = useState({
    department: '',
    salary_min: '',
    salary_max: '',
  });
  
  const debouncedSalaryMin = useDebounce(filters.salary_min, 1000);
  const debouncedSalaryMax = useDebounce(filters.salary_max, 1000);
  
  const [sortBy, setSortBy] = useState('employee_id');
  const [sortOrder, setSortOrder] = useState('ASC');
  
  const [exportType, setExportType] = useState('filtered');

  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const params = {
          department: filters.department,
          salary_min: debouncedSalaryMin,
          salary_max: debouncedSalaryMax,
          sort_by: sortBy,
          sort_order: sortOrder,
          page: page + 1,
          per_page: rowsPerPage
        };
        
        const response = await api.get('/employees', { params });
        
        setEmployees(response.data.data || []);
        setTotalEmployees(response.data.meta?.total || 0);
        
        if (response.data.meta?.departments) {
          setDepartments(response.data.meta.departments);
        }
      } catch (err) {
        console.error('Ошибка загрузки:', err);
        setError(err.response?.data?.error || err.message || 'Ошибка сервера');
      } finally {
        setLoading(false);
      }
    };

    fetchEmployees();
  }, [page, rowsPerPage, sortBy, sortOrder, filters.department, debouncedSalaryMin, debouncedSalaryMax]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
    if (name === 'department') {
      setPage(0);
    }
  };

  const handleSortChange = (columnId) => {
    if (sortBy === columnId) {
      setSortOrder(prev => prev === 'ASC' ? 'DESC' : 'ASC');
    } else {
      setSortBy(columnId);
      setSortOrder('ASC');
    }
    setPage(0);
  };

  const handleExport = async () => {
    try {
      setLoading(true);
      
      const params = {
        department: filters.department,
        salary_min: debouncedSalaryMin,
        salary_max: debouncedSalaryMax,
        sort_by: sortBy,
        sort_order: sortOrder,
        export_type: exportType
      };
      
      const response = await api.get('/export', {
        params,
        responseType: 'blob'
      });
      
      saveAs(new Blob([response.data]), 'employees.xlsx');
    } catch (err) {
      console.error('Ошибка экспорта:', err);
      setError(err.response?.data?.error || err.message || 'Ошибка экспорта');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (value) => {
    if (value === null || value === undefined) return '-';
    const num = Number(value);
    return isNaN(num) ? '-' : num.toFixed(2);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return '-';
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Управление сотрудниками
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Фильтры
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Отдел</InputLabel>
              <Select
                name="department"
                value={filters.department}
                onChange={handleFilterChange}
                label="Отдел"
                disabled={loading}
              >
                <MenuItem value="">Все отделы</MenuItem>
                {departments.map((dept, i) => (
                  <MenuItem key={i} value={dept}>{dept}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              name="salary_min"
              label="Мин. зарплата"
              type="number"
              value={filters.salary_min}
              onChange={handleFilterChange}
              disabled={loading}
              inputProps={{ min: 0 }}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              name="salary_max"
              label="Макс. зарплата"
              type="number"
              value={filters.salary_max}
              onChange={handleFilterChange}
              disabled={loading}
              inputProps={{ min: filters.salary_min || 0 }}
            />
          </Grid>
        </Grid>
      </Paper>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container alignItems="center" spacing={2}>
          <Grid item>
            <Typography>Всего сотрудников: {totalEmployees}</Typography>
          </Grid>
          <Grid item>
            <FormControlLabel
              control={
                <Switch
                  checked={exportType === 'all'}
                  onChange={(e) => setExportType(e.target.checked ? 'all' : 'filtered')}
                  disabled={loading}
                />
              }
              label="Экспортировать все"
            />
          </Grid>
          <Grid item>
            <Button
              variant="contained"
              onClick={handleExport}
              disabled={loading || totalEmployees === 0}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Экспорт в Excel
            </Button>
          </Grid>
        </Grid>
      </Paper>
      
      <Paper sx={{ mb: 3 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                {columns.map((column) => (
                  <TableCell
                    key={column.id}
                    onClick={() => column.sortable ? handleSortChange(column.id) : null}
                    sx={{
                      fontWeight: 'bold',
                      cursor: column.sortable ? 'pointer' : 'default',
                      '&:hover': {
                        backgroundColor: column.sortable ? 'action.hover' : 'inherit'
                      }
                    }}
                  >
                    <Box display="flex" alignItems="center">
                      {column.label}
                      {sortBy === column.id && (
                        <Box ml={1}>
                          {sortOrder === 'ASC' ? '↑' : '↓'}
                        </Box>
                      )}
                    </Box>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && employees.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={columns.length} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : employees.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={columns.length} align="center">
                    Нет данных для отображения
                  </TableCell>
                </TableRow>
              ) : (
                employees.map((employee) => (
                  <TableRow key={employee.id}>
                    <TableCell>{employee.id}</TableCell>
                    <TableCell>{employee.first_name}</TableCell>
                    <TableCell>{employee.last_name}</TableCell>
                    <TableCell>{employee.email}</TableCell>
                    <TableCell>{formatNumber(employee.salary)}</TableCell>
                    <TableCell>{formatDate(employee.hire_date)}</TableCell>
                    <TableCell>{employee.is_manager ? 'Да' : 'Нет'}</TableCell>
                    <TableCell>{employee.performance_rating}</TableCell>
                    <TableCell>{employee.department}</TableCell>
                    <TableCell>{formatNumber(employee.department_budget)}</TableCell>
                    <TableCell>{employee.projects_count}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        <TablePagination
          rowsPerPageOptions={[10, 20, 50]}
          component="div"
          count={totalEmployees}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          labelRowsPerPage="Строк на странице:"
          labelDisplayedRows={({ from, to, count }) => 
            `${from}-${to} из ${count !== -1 ? count : `более ${to}`}`
          }
        />
      </Paper>
    </Container>
  );
}

export default App;