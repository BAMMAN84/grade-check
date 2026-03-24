import streamlit as st
import json
import os
from fpdf import FPDF
import io

DATA_FILE = "student_profile.json"

# --- Helper Functions ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"name": "", "grade_level": "Freshman", "classes": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def calculate_gpa(data):
    total_points = 0
    total_credits = 0
    for course in data["classes"]:
        percent = course.get("current_percent", 0.0)
        credits = course.get("credits", 0)
        
        if percent >= 90: pt = 4.0
        elif percent >= 80: pt = 3.0
        elif percent >= 70: pt = 2.0
        elif percent >= 60: pt = 1.0
        else: pt = 0.0
            
        total_points += (pt * credits)
        total_credits += credits
    return total_points / total_credits if total_credits > 0 else 0.0

def get_study_hours(gpa):
    if gpa >= 3.0: return 0
    elif gpa >= 2.5: return 1
    elif gpa >= 2.0: return 3
    else: return 5

# --- Main App ---
st.set_page_config(page_title="Grade Check", page_icon="📝", layout="centered")
st.title("Program Grade Check")

data = load_data()

# Create standard web tabs
tab1, tab2, tab3 = st.tabs(["1. Profile Setup", "2. Weekly Data", "3. Report & PDF"])

# --- TAB 1: PROFILE SETUP ---
with tab1:
    st.header("Setup Your Profile")
    
    new_name = st.text_input("Student Name", value=data.get("name", ""))
    levels = ["Freshman", "Sophomore", "Junior", "Senior", "5th+"]
    current_level_index = levels.index(data["grade_level"]) if data.get("grade_level") in levels else 0
    new_level = st.selectbox("Grade Level", levels, index=current_level_index)
    
    st.subheader("Add a New Class")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_class_name = st.text_input("Class Name (e.g. ENG 101)")
    with col2:
        new_class_credits = st.number_input("Credits", min_value=1, max_value=6, value=3)
        
    if st.button("Add Class"):
        if new_class_name:
            if not any(c["name"] == new_class_name for c in data["classes"]):
                data["classes"].append({
                    "name": new_class_name, "credits": new_class_credits,
                    "previous_percent": None, "current_percent": 0.0, "assignments_this_week": 0
                })
                save_data(data)
                st.success(f"Added {new_class_name}!")
                st.rerun()

    st.subheader("Current Classes")
    for i, cls in enumerate(data["classes"]):
        st.write(f"**{cls['name']}** - {cls['credits']} Credits")
        if st.button(f"Remove {cls['name']}", key=f"del_{i}"):
            data["classes"].pop(i)
            save_data(data)
            st.rerun()

    # Save general profile info
    if new_name != data.get("name") or new_level != data.get("grade_level"):
        data["name"] = new_name
        data["grade_level"] = new_level
        save_data(data)

# --- TAB 2: WEEKLY DATA ---
with tab2:
    st.header("Weekly Grade Update")
    if not data["classes"]:
        st.info("Please add classes in the Profile Setup tab first.")
    else:
        with st.form("weekly_update_form"):
            updated_classes = []
            for i, course in enumerate(data["classes"]):
                st.subheader(course["name"])
                
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    grade_input = st.text_input(f"Grade (e.g. 85/100)", key=f"grade_{i}")
                with col2:
                    assign_input = st.number_input(f"# Assignments", min_value=0, value=0, key=f"assign_{i}")
                with col3:
                    st.write("") # Spacing
                    st.write("")
                    not_graded = st.checkbox("Not Graded", key=f"ng_{i}")
                
                updated_classes.append((course, grade_input, assign_input, not_graded))
                st.divider()
                
            if st.form_submit_button("Save Weekly Updates"):
                for course, grade_val, assign_val, ng_val in updated_classes:
                    course["assignments_this_week"] = assign_val
                    
                    if not ng_val and '/' in grade_val:
                        try:
                            earned, possible = map(float, grade_val.split('/'))
                            percent = (earned / possible) * 100
                            course["previous_percent"] = course["current_percent"]
                            course["current_percent"] = percent
                        except ValueError:
                            pass # Ignore bad input
                save_data(data)
                st.success("Weekly data saved successfully!")

# --- TAB 3: REPORT & PDF ---
with tab3:
    st.header("Report Preview")
    if not data["classes"]:
        st.info("Add classes and weekly data to generate a report.")
    else:
        gpa = calculate_gpa(data)
        study_hours = get_study_hours(gpa)
        
        st.write(f"**Student:** {data.get('name', 'Unknown')} ({data.get('grade_level', '')})")
        st.write(f"**Estimated GPA:** {gpa:.2f}")
        st.write(f"**Extra Study Hours Needed:** {study_hours}")
        
        st.subheader("Class Breakdown")
        for course in data["classes"]:
            st.write(f"- **{course['name']}**: {course['current_percent']:.2f}% (Assignments: {course['assignments_this_week']})")
        
        if st.button("Generate PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="Program Grade Check Report", ln=True, align='C')
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Student Name: {data.get('name', 'Unknown')}  |  Level: {data.get('grade_level', '')}", ln=True)
            pdf.line(10, 30, 200, 30)
            pdf.ln(10)

            for course in data["classes"]:
                curr = course["current_percent"]
                prev = course["previous_percent"]
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(200, 8, txt=f"- {course['name']}: {curr:.2f}% (Assignments: {course['assignments_this_week']})", ln=True)
                
                if prev is not None and prev > 0:
                    diff = curr - prev
                    trend = "Improved" if diff >= 0 else "Dropped"
                    pdf.set_font("Arial", 'I', 11)
                    pdf.cell(200, 6, txt=f"   Trend: {trend} by {abs(diff):.2f}%", ln=True)
                pdf.ln(2)

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt=f"Estimated GPA: {gpa:.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Extra Study Hours Needed: {study_hours}", ln=True)

            pdf_bytes = pdf.output(dest="S").encode("latin-1")
            
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_bytes,
                file_name=f"{data.get('name', 'Student').replace(' ', '_')}_Report.pdf",
                mime="application/pdf"
            )

