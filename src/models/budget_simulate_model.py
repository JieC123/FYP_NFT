import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.cluster import KMeans
from sklearn.model_selection import cross_val_score

class BudgetSimulateModel:
    def __init__(self):
        try:
            # Load advertising dataset
            self.ad_data = pd.read_csv('Advertising_Budget_and_Sales.csv')
            self.ad_data = self.ad_data.drop(columns=['Sales'])

            # Load staff cost dataset
            self.staff_data = pd.read_csv('event_staff_costs.csv')
            
            # Train advertising models
            self.tv_model = self.train_ad_model(target_column='TV Ad Budget')
            self.radio_model = self.train_ad_model(target_column='Radio Ad Budget')
            self.newspaper_model = self.train_ad_model(target_column='Newspaper Ad Budget')
            
            # Train staff cost model
            self.staff_model = self._train_staff_cost_model()
            
            # Store average daily rates for staff
            self.avg_daily_rates = self.staff_data.groupby(['Role', 'Experience_Level'])['Daily_Rate'].mean().to_dict()
            
            # Load venue dataset
            self.venue_data = pd.read_csv('venue_rental_data.csv')
            
            # Train venue cost model
            self.venue_models = self._train_venue_models()
            
            # Calculate capacity ranges for each venue type
            self.venue_capacity_ranges = self._calculate_venue_ranges()
            
        except Exception as e:
            print(f"Error initializing BudgetSimulateModel: {e}")
            raise

    # Existing advertising model methods
    def train_ad_model(self, target_column):
        try:
            X = self.ad_data.drop(columns=[target_column])
            y = self.ad_data[target_column]

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model = LinearRegression()
            model.fit(X_train, y_train)

            # Store test predictions and actuals for overall metrics
            if not hasattr(self, 'all_ad_predictions'):
                self.all_ad_predictions = []
                self.all_ad_actuals = []
            
            y_pred = model.predict(X_test)
            self.all_ad_predictions.extend(y_pred)
            self.all_ad_actuals.extend(y_test)

            # Calculate and display overall metrics after training all models
            if target_column == 'Newspaper Ad Budget':  # Last model to be trained
                mse = mean_squared_error(self.all_ad_actuals, self.all_ad_predictions)
                rmse = np.sqrt(mse)
                r2 = r2_score(self.all_ad_actuals, self.all_ad_predictions)
                
                print(f"\nOverall Advertising Model Metrics:")
                # print(f"MSE: {mse:.4f}")
                print(f"RMSE: {rmse:.4f}")
                print(f"R² Score: {r2:.4f}")

            return model
        except Exception as e:
            print(f"Error training model for {target_column}: {e}")
            raise

    def predict_cost(self, model):
        try:
            feature_names = model.feature_names_in_
            input_data = pd.DataFrame([[0] * len(feature_names)], columns=feature_names)
            prediction = model.predict(input_data)[0]
            adjusted_prediction = prediction * 1000
            print(f"Raw Prediction: {prediction}, Adjusted Prediction (x1000): {adjusted_prediction}")
            return adjusted_prediction
        except Exception as e:
            print(f"Error in predict_cost: {e}")
            raise

    # New staff cost model methods
    def _train_staff_cost_model(self):
        try:
            categorical_features = ['Role', 'Experience_Level', 'Event_Type']
            preprocessor = ColumnTransformer(
                transformers=[
                    ('cat', OneHotEncoder(drop='first', sparse_output=False), categorical_features)
                ])

            model = Pipeline([
                ('preprocessor', preprocessor),
                ('regressor', LinearRegression())
            ])

            X = self.staff_data[['Role', 'Experience_Level', 'Event_Type']]
            y = self.staff_data['Daily_Rate']

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)
            print(f"\nStaff Cost Model Metrics:")
            # print(f"MSE: {mse:.4f}")
            print(f"RMSE: {rmse:.4f}")
            print(f"R² Score: {r2:.4f}")

            return model
        except Exception as e:
            print(f"Error training staff cost model: {e}")
            return None

    def predict_staff_cost(self, role, event_type, experience_level='Mid'):
        try:
            if self.staff_model is not None:
                # Try using the trained model first
                input_data = pd.DataFrame({
                    'Role': [role],
                    'Experience_Level': [experience_level],
                    'Event_Type': [event_type]
                })
                predicted_rate = self.staff_model.predict(input_data)[0]
            else:
                # Fallback to using average rates
                predicted_rate = None

            # If prediction failed or is unreasonable, use average rates
            if predicted_rate is None or predicted_rate <= 0 or predicted_rate > 10000:
                # Get average rate for this combination
                mask = (self.staff_data['Role'] == role) & \
                      (self.staff_data['Event_Type'] == event_type) & \
                      (self.staff_data['Experience_Level'] == experience_level)
                avg_rate = self.staff_data[mask]['Daily_Rate'].mean()
                
                # If no exact match, try just role average
                if pd.isna(avg_rate):
                    avg_rate = self.staff_data[self.staff_data['Role'] == role]['Daily_Rate'].mean()
                
                # If still no match, use overall average
                if pd.isna(avg_rate):
                    avg_rate = self.staff_data['Daily_Rate'].mean()
                
                predicted_rate = avg_rate

            return round(float(predicted_rate), 2)

        except Exception as e:
            print(f"Error predicting staff cost: {e}")
            # Return a default rate if everything fails
            return self.staff_data['Daily_Rate'].mean()

    def calculate_total_staff_cost(self, staff_requirements, event_type, event_duration):
        try:
            total_cost = 0
            cost_breakdown = {}

            print(f"Processing staff requirements: {staff_requirements}")
            print(f"Event type: {event_type}")
            print(f"Event duration: {event_duration}")

            for role, count in staff_requirements.items():
                try:
                    daily_rate = self.predict_staff_cost(role, event_type)
                    role_total = daily_rate * int(count) * int(event_duration)
                    total_cost += role_total
                    cost_breakdown[role] = {
                        'daily_rate': daily_rate,
                        'count': count,
                        'total': role_total
                    }
                    print(f"Processed {role}: daily_rate={daily_rate}, count={count}, total={role_total}")
                except Exception as e:
                    print(f"Error processing role {role}: {e}")
                    continue

            return {
                'total_cost': round(total_cost, 2),
                'breakdown': cost_breakdown
            }
        except Exception as e:
            print(f"Error calculating total staff cost: {e}")
            raise

    def predict_budget(self, total_food_cost, marketing_option, staff_requirements=None, event_type=None, event_duration=1, venue_cost=0, miscellaneous_cost=0):
        try:
            # Calculate marketing cost
            marketing_cost = 0
            if marketing_option == 'TV Ad':
                marketing_cost = self.predict_cost(self.tv_model)
            elif marketing_option == 'Radio Ad':
                marketing_cost = self.predict_cost(self.radio_model)
            elif marketing_option == 'Newspaper Ad':
                marketing_cost = self.predict_cost(self.newspaper_model)
            elif marketing_option == 'TV + Radio':
                marketing_cost = self.predict_cost(self.tv_model) + self.predict_cost(self.radio_model)
            elif marketing_option == 'TV + Newspaper':
                marketing_cost = self.predict_cost(self.tv_model) + self.predict_cost(self.newspaper_model)
            elif marketing_option == 'Radio + Newspaper':
                marketing_cost = self.predict_cost(self.radio_model) + self.predict_cost(self.newspaper_model)
            elif marketing_option == 'TV + Radio + Newspaper':
                marketing_cost = (
                    self.predict_cost(self.tv_model) +
                    self.predict_cost(self.radio_model) +
                    self.predict_cost(self.newspaper_model)
                )

            # Calculate staff cost if requirements provided
            staff_cost = 0
            staff_breakdown = {}
            if staff_requirements and event_type:
                print(f"Calculating staff costs for: {staff_requirements}")  # Debug log
                staff_result = self.calculate_total_staff_cost(staff_requirements, event_type, event_duration)
                staff_cost = staff_result['total_cost']
                staff_breakdown = staff_result['breakdown']
                print(f"Staff calculation result: {staff_result}")  # Debug log

            # Calculate total budget including venue and miscellaneous costs
            total_budget = (
                float(total_food_cost) + 
                float(marketing_cost) + 
                float(staff_cost) + 
                float(venue_cost) + 
                float(miscellaneous_cost)
            )
            
            return {
                'total_budget': round(total_budget, 2),
                'total_food_cost': round(float(total_food_cost), 2),
                'marketing_cost': round(marketing_cost, 2),
                'staff_cost': round(staff_cost, 2),
                'venue_cost': round(float(venue_cost), 2),
                'miscellaneous_cost': round(float(miscellaneous_cost), 2),
                'staff_breakdown': staff_breakdown
            }
            
        except Exception as e:
            print(f"Error in predict_budget: {e}")
            raise

    def _calculate_venue_ranges(self):
        """Calculate capacity ranges for each venue type using clustering"""
        venue_ranges = {}
        
        for venue_type in self.venue_data['VenueType'].unique():
            venue_data = self.venue_data[self.venue_data['VenueType'] == venue_type]
            attendances = venue_data['Attendance'].values.reshape(-1, 1)
            
            if len(attendances) > 2:  # Only cluster if we have enough data points
                # Use 3 clusters for small, medium, and large capacities
                kmeans = KMeans(n_clusters=3, random_state=42)
                kmeans.fit(attendances)
                
                # Get cluster centers and sort them
                centers = sorted([int(c[0]) for c in kmeans.cluster_centers_])
                
                venue_ranges[venue_type] = {
                    'small': f"Up to {centers[0]} people",
                    'medium': f"{centers[0] + 1} - {centers[1]} people",
                    'large': f"Over {centers[1]} people",
                    'centers': centers  # Store actual centers for cost prediction
                }
            else:
                # If not enough data, use simple ranges
                max_attendance = venue_data['Attendance'].max()
                venue_ranges[venue_type] = {
                    'small': f"Up to {max_attendance//3} people",
                    'medium': f"{max_attendance//3 + 1} - {max_attendance*2//3} people",
                    'large': f"Over {max_attendance*2//3} people",
                    'centers': [max_attendance//3, max_attendance*2//3, max_attendance]
                }
                
        return venue_ranges

    def _train_venue_models(self):
        """Train linear regression models for each venue type"""
        venue_models = {}
        
        # Collect all predictions for overall evaluation
        all_predictions = []
        all_actuals = []
        
        for venue_type in self.venue_data['VenueType'].unique():
            venue_data = self.venue_data[self.venue_data['VenueType'] == venue_type]
            
            if len(venue_data) > 1:
                X = venue_data[['Attendance']].values
                y = venue_data['OneDayCost'].values
                
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                model = LinearRegression()
                model.fit(X_train, y_train)
                
                y_pred = model.predict(X_test)
                all_predictions.extend(y_pred)
                all_actuals.extend(y_test)
                
                venue_models[venue_type] = model
        
        # Calculate overall metrics for venue models
        if all_predictions:
            mse = mean_squared_error(all_actuals, all_predictions)
            rmse = np.sqrt(mse)
            r2 = r2_score(all_actuals, all_predictions)
            print(f"\nVenue Cost Model Metrics:")
            # print(f"MSE: {mse:.4f}")
            print(f"RMSE: {rmse:.4f}")
            print(f"R² Score: {r2:.4f}")
                
        return venue_models

    def predict_venue_cost(self, venue_type, capacity):
        """Predict venue cost based on type and capacity"""
        try:
            if venue_type in self.venue_models:
                predicted_cost = self.venue_models[venue_type].predict([[capacity]])[0]
                return max(predicted_cost, 0)  # Ensure non-negative cost
            return None
        except Exception as e:
            print(f"Error predicting venue cost: {e}")
            return None

    def get_venue_options(self):
        """Get all venue options with their capacity ranges and predicted costs"""
        venue_options = []
        
        for venue_type, ranges in self.venue_capacity_ranges.items():
            for size, capacity_range in ranges.items():
                if size != 'centers':  # Skip the centers entry
                    # Get the center point for this range for cost prediction
                    center_idx = 0 if size == 'small' else 1 if size == 'medium' else 2
                    capacity = ranges['centers'][center_idx]
                    
                    # Predict cost for this capacity
                    cost = self.predict_venue_cost(venue_type, capacity)
                    
                    if cost is not None:
                        venue_options.append({
                            'id': f"{venue_type}_{size}",
                            'name': f"{venue_type.replace('_', ' ')} ({capacity_range})",
                            'type': venue_type,
                            'capacity': capacity,
                            'daily_cost': round(cost, 2)
                        })
        
        return sorted(venue_options, key=lambda x: x['daily_cost'])

    def calculate_ad_model_cv_scores(self):
        """Calculate cross-validation scores for each advertising model"""
        try:
            cv_results = {}
            
            # Calculate CV scores for TV ad model
            X = self.ad_data.drop(columns=['TV Ad Budget'])
            y = self.ad_data['TV Ad Budget']
            tv_scores = cross_val_score(LinearRegression(), X, y, cv=5, scoring='r2')
            cv_results['TV Ad Budget'] = {
                'mean_r2': tv_scores.mean(),
                'std_r2': tv_scores.std(),
                'cv_scores': tv_scores
            }
            
            # Calculate CV scores for Radio ad model
            X = self.ad_data.drop(columns=['Radio Ad Budget'])
            y = self.ad_data['Radio Ad Budget']
            radio_scores = cross_val_score(LinearRegression(), X, y, cv=5, scoring='r2')
            cv_results['Radio Ad Budget'] = {
                'mean_r2': radio_scores.mean(),
                'std_r2': radio_scores.std(),
                'cv_scores': radio_scores
            }
            
            # Calculate CV scores for Newspaper ad model
            X = self.ad_data.drop(columns=['Newspaper Ad Budget'])
            y = self.ad_data['Newspaper Ad Budget']
            newspaper_scores = cross_val_score(LinearRegression(), X, y, cv=5, scoring='r2')
            cv_results['Newspaper Ad Budget'] = {
                'mean_r2': newspaper_scores.mean(),
                'std_r2': newspaper_scores.std(),
                'cv_scores': newspaper_scores
            }
            
            # Print results
            print("\nCross-Validation Results:")
            for model_name, scores in cv_results.items():
                print(f"\n{model_name}:")
                print(f"Mean R² Score: {scores['mean_r2']:.3f} (+/- {scores['std_r2']*2:.3f})")
                print(f"Individual CV Scores: {scores['cv_scores']}")
            
            return cv_results
            
        except Exception as e:
            print(f"Error calculating cross-validation scores: {e}")
            raise
