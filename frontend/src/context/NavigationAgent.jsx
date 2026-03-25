import React, { createContext, useContext, useReducer, useEffect } from 'react';

// Navigation action types
export const NAVIGATE_RESULTS = 'NAVIGATE_RESULTS';
export const NAVIGATE_DETAIL = 'NAVIGATE_DETAIL';
export const NAVIGATE_HOME = 'NAVIGATE_HOME';
export const HIGHLIGHT_HOSPITAL = 'HIGHLIGHT_HOSPITAL';
export const CLEAR_HIGHLIGHT = 'CLEAR_HIGHLIGHT';

// Context state
const initialState = {
  currentView: 'home',
  highlightedHospital: null,
  hospitalData: null,
  searchQuery: '',
  isLoading: false,
  error: null
};

// Reducer function
const navigationReducer = (state, action) => {
  switch (action.type) {
    case NAVIGATE_RESULTS:
      return { ...state, currentView: 'results', highlightedHospital: null };
    case NAVIGATE_DETAIL:
      return { ...state, currentView: 'detail', highlightedHospital: action.payload };
    case NAVIGATE_HOME:
      return { ...state, currentView: 'home', highlightedHospital: null };
    case HIGHLIGHT_HOSPITAL:
      return { ...state, highlightedHospital: action.payload };
    case CLEAR_HIGHLIGHT:
      return { ...state, highlightedHospital: null };
    case 'SET_HOSPITAL_DATA':
      return { ...state, hospitalData: action.payload };
    case 'SET_SEARCH_QUERY':
      return { ...state, searchQuery: action.payload };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    default:
      return state;
  }
};

// Create context
const NavigationContext = createContext();

// Provider component
export const NavigationProvider = ({ children }) => {
  const [state, dispatch] = useReducer(navigationReducer, initialState);

  // Navigation actions
  const navigateToResults = (query) => {
    dispatch({ type: 'SET_SEARCH_QUERY', payload: query });
    dispatch({ type: NAVIGATE_RESULTS });
  };

  const navigateToDetail = (hospital) => {
    dispatch({ type: NAVIGATE_DETAIL, payload: hospital });
  };

  const navigateToHome = () => {
    dispatch({ type: NAVIGATE_HOME });
  };

  const highlightHospital = (hospital) => {
    dispatch({ type: HIGHLIGHT_HOSPITAL, payload: hospital });
  };

  const clearHighlight = () => {
    dispatch({ type: CLEAR_HIGHLIGHT });
  };

  // Set hospital data (for passing between components)
  const setHospitalData = (data) => {
    dispatch({ type: 'SET_HOSPITAL_DATA', payload: data });
  };

  // Set loading state
  const setLoading = (loading) => {
    dispatch({ type: 'SET_LOADING', payload: loading });
  };

  // Set error state
  const setError = (error) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  };

  return (
    <NavigationContext.Provider value={{
      state,
      navigateToResults,
      navigateToDetail,
      navigateToHome,
      highlightHospital,
      clearHighlight,
      setHospitalData,
      setLoading,
      setError
    }}>
      {children}
    </NavigationContext.Provider>
  );
};

// Custom hook for consuming context
export const useNavigation = () => {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
};