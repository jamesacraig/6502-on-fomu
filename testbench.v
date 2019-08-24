`timescale 1 ns / 100 ps
module testbench;
   reg clk48;
   wire led_rgb0;
   wire led_rgb1;
   wire led_rgb2;
   
   initial begin
      clk48=0;
      
      $display("Starting simulation");
      $dumpfile("test.vcd");
      $dumpvars(0, top);
      #100000
      $display("Simulation complete");
      $finish;

   end

   always #10 clk48=~clk48;

   top top(
	   .clk48(clk48),
	   .led_rgb0(led_rgb0),
	   .led_rgb1(led_rgb1),
	   .led_rgb2(led_rgb2)
	   );
   
endmodule // testbench

  
