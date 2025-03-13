from fastapi import FastAPI, File, UploadFile, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
import io

app = FastAPI(
    title="Waypoint, The All-In-One Non-Discriminatory Testing Application",
    description="A tool for running non-discriminatory compliance tests including ADP, ACP, Cafeteria Plan, Health FSA, DCAP, and HRA.",
    version="3.0.0"
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (adjust for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files from /Users/jedcrisp/adp_backend
# (Make sure that your frontend build files are located in this directory or adjust accordingly)
app.mount("/", StaticFiles(directory="/Users/jedcrisp/adp_backend", html=True), name="static")

# Define required columns for each test
TEST_COLUMN_REQUIREMENTS = {
    "adp": ["Name", "Compensation", "Employee Deferral", "HCE"],
    "acp": ["Name", "Compensation", "Employer Match", "HCE"],
    "key_employee": ["Name", "Compensation", "Cafeteria Plan Benefits", "Key Employee"],
    "eligibility": ["Name", "HCE"],
    "classification": ["Name", "Eligible for Cafeteria Plan"],
    "benefit": ["Name", "Cafeteria Plan Benefits", "HCE"],
    "health_fsa_eligibility": ["Name", "Eligible for FSA", "HCE"],
    "health_fsa_benefits": ["Name", "HCI", "Health FSA Benefits"],
    "dcap_eligibility": ["Name", "HCE", "Eligible for DCAP"],
    "dcap_owners": ["Name", "Ownership %", "DCAP Benefits"],
    "dcap_55_benefits": ["Name", "HCE", "DCAP Benefits"],
    "dcap_contributions": ["Name", "DCAP Contributions", "HCE"],
    "hra_benefits": ["Name", "HRA Benefits", "HCE"],
    "hra_eligibility": ["Name", "HCI", "Eligible for HRA"],
}

# Dynamic CSV Upload Route
@app.post("/upload-csv/{test_type}")
async def upload_csv(test_type: str, file: UploadFile = File(...)):
    if test_type not in TEST_COLUMN_REQUIREMENTS:
        raise HTTPException(status_code=400, detail="Invalid test type")
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        # Validate required columns
        required_columns = TEST_COLUMN_REQUIREMENTS[test_type]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"Missing columns: {missing_columns}")
        # Run the appropriate test logic
        result = run_test(df, test_type)
        return {"Test Type": test_type, "Result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# Function to Run Different Tests
def run_test(df, test_type):
    try:
        # ADP TEST
        if test_type == "adp":
            hce_group = df[df["HCE"] == "Yes"]
            nhce_group = df[df["HCE"] == "No"]
            hce_adp = (
                (hce_group["Employee Deferral"].sum() / hce_group["Compensation"].sum()) * 100
                if not hce_group.empty and hce_group["Compensation"].sum() > 0 else 0
            )
            nhce_adp = (
                (nhce_group["Employee Deferral"].sum() / nhce_group["Compensation"].sum()) * 100
                if not nhce_group.empty and nhce_group["Compensation"].sum() > 0 else 0
            )
            test_result = "Passed" if hce_adp <= (nhce_adp * 1.25) else "Failed"
            return {
                "HCE ADP (%)": round(hce_adp, 2),
                "NHCE ADP (%)": round(nhce_adp, 2),
                "Test Result": test_result
            }

        # ACP TEST
        if test_type == "acp":
            hce_group = df[df["HCE"] == "Yes"]
            nhce_group = df[df["HCE"] == "No"]
            hce_acp = (
                hce_group["Employer Match"].sum() / hce_group["Compensation"].sum() * 100
                if hce_group["Compensation"].sum() > 0 else 0
            )
            nhce_acp = (
                nhce_group["Employer Match"].sum() / nhce_group["Compensation"].sum() * 100
                if nhce_group["Compensation"].sum() > 0 else 0
            )
            acp_test_result = "Passed" if hce_acp <= (nhce_acp * 1.25) else "Failed"
            return {
                "HCE_Average_Contribution (%)": round(hce_acp, 2),
                "NHCE_Average_Contribution (%)": round(nhce_acp, 2),
                "ACP_Test_Result": acp_test_result
            }
        
        # Key Employee Test
        if test_type == "key_employee":
            total_employees = len(df)
            key_employees = df[df["Key Employee"] == "Yes"].shape[0]
            key_percentage = (key_employees / total_employees) * 100 if total_employees > 0 else 0
            test_result = "Passed" if key_percentage <= 20 else "Failed"
            return {
                "Total Employees": total_employees,
                "Key Employees": key_employees,
                "Key Employee Percentage": round(key_percentage, 2),
                "Test Result": test_result
            }
        
        # Eligibility Test (using HCE as an example)
        if test_type == "eligibility":
            total_employees = len(df)
            hce_count = df[df["HCE"] == "Yes"].shape[0]
            hce_percentage = (hce_count / total_employees) * 100 if total_employees > 0 else 0
            test_result = "Passed" if hce_percentage <= 40 else "Failed"
            return {
                "Total Employees": total_employees,
                "HCE Count": hce_count,
                "HCE Percentage (%)": round(hce_percentage, 2),
                "Test Result": test_result
            }
        
        # Classification Test
        if test_type == "classification":
            total_employees = len(df)
            eligible = df[df["Eligible for Cafeteria Plan"] == "Yes"].shape[0]
            eligibility_pct = (eligible / total_employees) * 100 if total_employees > 0 else 0
            test_result = "Passed" if eligibility_pct >= 70 else "Failed"
            return {
                "Total Employees": total_employees,
                "Eligible for Cafeteria Plan": eligible,
                "Eligibility Percentage (%)": round(eligibility_pct, 2),
                "Test Result": test_result
            }
        
        # Benefit Test (Cafeteria Plan Benefits)
        if test_type == "benefit":
            hce_group = df[df["HCE"] == "Yes"]
            nhce_group = df[df["HCE"] == "No"]
            hce_avg_benefits = hce_group["Cafeteria Plan Benefits"].mean()
            nhce_avg_benefits = nhce_group["Cafeteria Plan Benefits"].mean()
            hce_avg_benefits = 0 if pd.isna(hce_avg_benefits) else hce_avg_benefits
            nhce_avg_benefits = 0 if pd.isna(nhce_avg_benefits) else nhce_avg_benefits
            ratio = (nhce_avg_benefits / hce_avg_benefits) * 100 if hce_avg_benefits > 0 else 0
            test_result = "Passed" if ratio >= 55 else "Failed"
            return {
                "HCE Avg Benefits": round(hce_avg_benefits, 2),
                "Non-HCE Avg Benefits": round(nhce_avg_benefits, 2),
                "Benefit Ratio (%)": round(ratio, 2),
                "Test Result": test_result
            }
        
        # Health FSA Eligibility Test
        if test_type == "health_fsa_eligibility":
            total_employees = len(df)
            eligible = df[df["Eligible for FSA"] == "Yes"].shape[0]
            eligibility_percentage = (eligible / total_employees * 100) if total_employees > 0 else 0
            test_result = "Passed" if eligibility_percentage >= 70 else "Failed"
            return {
                "Total Employees": total_employees,
                "Eligible for FSA": eligible,
                "Health FSA Eligibility Percentage (%)": round(eligibility_percentage, 2),
                "Health FSA Eligibility Test Result": test_result
            }
        
        # Health FSA Benefits Test
        if test_type == "health_fsa_benefits":
            hci_group = df[df["HCI"] == "Yes"]
            non_hci_group = df[df["HCI"] == "No"]
            hci_avg = hci_group["Health FSA Benefits"].mean() if not hci_group.empty else 0
            non_hci_avg = non_hci_group["Health FSA Benefits"].mean() if not non_hci_group.empty else 0
            hci_avg = 0 if pd.isna(hci_avg) else hci_avg
            non_hci_avg = 0 if pd.isna(non_hci_avg) else non_hci_avg
            ratio = (non_hci_avg / hci_avg * 100) if hci_avg > 0 else 0
            test_result = "Passed" if ratio >= 100 else "Failed"
            return {
                "HCI Average Benefits": round(hci_avg, 2),
                "Non-HCI Average Benefits": round(non_hci_avg, 2),
                "Benefit Ratio (%)": round(ratio, 2),
                "Test Result": test_result
            }
        
        # DCAP Eligibility Test
        if test_type == "dcap_eligibility":
            total_employees = len(df)
            eligible_employees = df[df["Eligible for DCAP"] == "Yes"].shape[0]
            eligibility_percentage = ((eligible_employees / total_employees) * 100 if total_employees > 0 else 0)
            test_result = "Passed" if eligibility_percentage >= 50 else "Failed"
            return {
                "Total Employees": total_employees,
                "Eligible Employees": eligible_employees,
                "DCAP Eligibility Percentage (%)": round(eligibility_percentage, 2),
                "DCAP Eligibility Test Result": test_result
            }
        
        # DCAP Owners Test
        if test_type == "dcap_owners":
            owners = df[df["Ownership %"] > 0]
            if owners.empty:
                return {"message": "No owners found."}
            avg_dcap_benefits = owners["DCAP Benefits"].mean()
            test_result = "Passed" if avg_dcap_benefits >= 100 else "Failed"
            return {
                "Average DCAP Benefits for Owners": round(avg_dcap_benefits, 2),
                "Test Result": test_result
            }
        
        # DCAP 55% Benefits Test
        if test_type == "dcap_55_benefits":
            hce_group = df[df["HCE"] == "Yes"]
            nhce_group = df[df["HCE"] == "No"]
            hce_avg_benefits = hce_group["DCAP Benefits"].mean()
            nhce_avg_benefits = nhce_group["DCAP Benefits"].mean()
            hce_avg_benefits = 0 if pd.isna(hce_avg_benefits) else hce_avg_benefits
            nhce_avg_benefits = 0 if pd.isna(nhce_avg_benefits) else nhce_avg_benefits
            ratio = (nhce_avg_benefits / hce_avg_benefits) * 100 if hce_avg_benefits > 0 else 0
            test_result = "Passed" if ratio >= 55 else "Failed"
            return {
                "HCE Avg Benefits": round(hce_avg_benefits, 2),
                "Non-HCE Avg Benefits": round(nhce_avg_benefits, 2),
                "Ratio (%)": round(ratio, 2),
                "Test Result": test_result
            }
        
        # DCAP Contributions Test
        if test_type == "dcap_contributions":
            hce_group = df[df["HCE"] == "Yes"]
            nhce_group = df[df["HCE"] == "No"]
            hce_avg_contributions = hce_group["DCAP Contributions"].mean()
            nhce_avg_contributions = nhce_group["DCAP Contributions"].mean()
            hce_avg_contributions = 0 if pd.isna(hce_avg_contributions) else hce_avg_contributions
            nhce_avg_contributions = 0 if pd.isna(nhce_avg_contributions) else nhce_avg_contributions
            test_result = "Passed" if hce_avg_contributions <= (nhce_avg_contributions * 1.25) else "Failed"
            return {
                "HCE Average Contributions": round(hce_avg_contributions, 2),
                "NHCE Average Contributions": round(nhce_avg_contributions, 2),
                "Test Result": test_result
            }
        
        # HRA Eligibility Test
        if test_type == "hra_eligibility":
            hce_group = df[df["HCE"] == "Yes"]
            nhce_group = df[df["HCE"] == "No"]
            hce_eligibility_pct = ((hce_group[hce_group["Eligible for HRA"] == "Yes"].shape[0] / len(hce_group)) * 100
                                   if len(hce_group) > 0 else 0)
            nhce_eligibility_pct = ((nhce_group[nhce_group["Eligible for HRA"] == "Yes"].shape[0] / len(nhce_group)) * 100
                                    if len(nhce_group) > 0 else 0)
            ratio = (nhce_eligibility_pct / hce_eligibility_pct) * 100 if hce_eligibility_pct > 0 else 0
            test_result = "Passed" if ratio >= 70 else "Failed"
            return {
                "HCE Eligibility (%)": round(hce_eligibility_pct, 2),
                "Non-HCE Eligibility (%)": round(nhce_eligibility_pct, 2),
                "Ratio (%)": round(ratio, 2),
                "Test Result": test_result
            }
        
        # HRA Benefits Test
        if test_type == "hra_benefits":
            hce_group = df[df["HCE"] == "Yes"]
            nhce_group = df[df["HCE"] == "No"]
            hce_avg = hce_group["HRA Benefits"].mean() if not hce_group.empty else 0
            nhce_avg = nhce_group["HRA Benefits"].mean() if not nhce_group.empty else 0
            test_result = "Passed" if hce_avg >= nhce_avg else "Failed"
            return {
                "HCE Average Benefits": round(hce_avg, 2),
                "NHCE Average Benefits": round(nhce_avg, 2),
                "Test Result": test_result
            }
        
        return {"message": "Test logic not implemented yet"}
    except Exception as e:
        return {"error": f"Test execution error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
