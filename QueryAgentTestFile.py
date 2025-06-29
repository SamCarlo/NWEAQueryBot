from QueryAgent import QueryAgent
import unittest

class QueryAgentTest(unittest.TestCase):

    def setUp(self):
        self.agent = QueryAgent()
        self.agent.send_first_message('Check the schema')

    #def test_send_first_message(self):
    #    print("TESTING FIRST MESSAGE FOR FUNCTION CALL")
    #    prompt = 'Go ahead and check the schema'
    #    self.agent.send_first_message(prompt)
    #    actual = bool(self.agent.response.function_call)
    #    print(f"Full response: {self.agent.response}")
    #    self.assertTrue(actual, "Expected function_call content in responses.")

    def test_get_schema(self):
        self.agent.get_schema()
        api_responses = self.agent.api_requests_and_responses
        schema = api_responses[-1][2]
        print("\nSchema: \n\n" + schema)
        self.assertTrue(api_responses, "Nothing appended to api_responses[].")
    

    def test_send_api_repsonse(self):
        print("TEST SEND A FUNCTION_CALL RESULT BACK TO CHAT")
if __name__ == "__main__":
    unittest.main()

